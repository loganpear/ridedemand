"""
Ride availability microservice for the ridedemand project.

This service lets drivers create ride listings and riders search for available
rides on specific dates. It stores listings in a local SQLite database and
trusts user identity via JWTs issued by the user service.
"""

import json
import logging
import os
import sqlite3
from typing import Optional

import requests
from flask import Flask, request

from common.auth import get_username_from_jwt, is_valid_jwt

logger = logging.getLogger(__name__)

app = Flask(__name__)
db_name = "availability.db"
sql_file = "availability.sql"
db_flag = False


def create_db() -> None:
	"""Create the SQLite database from the SQL schema file if it does not exist."""
	conn: Optional[sqlite3.Connection] = None
	try:
		conn = sqlite3.connect(db_name)
		with open(sql_file, 'r') as sql_startup:
			init_db = sql_startup.read()
		cursor = conn.cursor()
		cursor.executescript(init_db)
		conn.commit()
		global db_flag
		db_flag = True
	except Exception:
		logger.exception("Error in create_db")
	finally:
		if conn is not None:
			conn.close()


def get_db() -> sqlite3.Connection:
	"""Return a SQLite connection, creating the database on first use."""
	if not db_flag:
		create_db()
	conn = sqlite3.connect(db_name)
	curr = conn.cursor()
	curr.execute("PRAGMA foreign_keys = ON;")
	return conn


@app.route('/clear', methods=['GET'])
def clear() -> str:
	"""Reset the availability database by deleting and recreating the file."""
	if os.path.exists(db_name):
		os.remove(db_name)
	create_db()
	logger.info("Database has been cleared and recreated")
	return "The database has been cleared"

@app.route('/listing', methods=['POST'])
def listing() -> str:
	"""
	Create a new availability listing for a driver on a specific date.

	Expected form fields:
	- ride_date: ISO date string (YYYY-MM-DD)
	- ride_time: 24h time string (HH:MM)
	- price: decimal price in dollars (e.g. 9.99)
	- listingid: integer ID chosen by the caller
	"""
	ride_date = request.form.get("ride_date")
	ride_time = request.form.get("ride_time")
	price_cents = int(float(request.form.get("price")) * 100)
	listing_id = request.form.get("listingid")
	jwt = request.headers.get('Authorization')

	if not ride_date or not ride_time or not listing_id:
		return json.dumps({"status": 2, "error": "INVALID_INPUT"})

	if not is_valid_jwt(jwt):
		return json.dumps({"status": 2, "error": "UNAUTHORIZED"})
	username = get_username_from_jwt(jwt) or ""

	conn: Optional[sqlite3.Connection] = None
	try:
		# ensure the user is valid and a driver
		data = requests.get(
			"http://user:5000/get_driver_status",
			params={"username": username}
		).json()
		if data.get("driver") != 1:
			return json.dumps({"status": 2, "error": "NOT_DRIVER"})

		conn = get_db()
		curr = conn.cursor()

		curr.execute("""
			INSERT INTO listings VALUES(?,?,?,?,?);
			""", (listing_id, username, ride_date, ride_time, price_cents))
		conn.commit()
		conn.close()
		return json.dumps({"status": 1})

	except Exception:
		logger.exception("Error in listing")
		try:
			if conn is not None:
				conn.close()
		except Exception:
			pass
		return json.dumps({"status": 2, "error": "INTERNAL_ERROR"})


@app.route('/search', methods=['GET'])
def search() -> str:
	"""
	Search for available ride listings on a specific date for a rider.

	Query parameters:
	- ride_date: ISO date string (YYYY-MM-DD)
	- ride_time (optional): 24h time string (HH:MM) to filter by time
	"""
	ride_date = request.args.get("ride_date")
	ride_time = request.args.get("ride_time")
	jwt = request.headers.get('Authorization')
	listings = []

	if not is_valid_jwt(jwt):
		return json.dumps({"status": 2, "error": "UNAUTHORIZED", "data": listings})
	rider_username = get_username_from_jwt(jwt)

	conn: Optional[sqlite3.Connection] = None
	try:
		# ensure the user is valid and a rider
		data = requests.get(
			"http://user:5000/get_driver_status",
			params={"username": rider_username}
		).json()
		if data.get("driver") != 0:
			return json.dumps({"status": 2, "error": "NOT_RIDER", "data": listings})

		# get price and listing id
		conn = get_db()
		curr = conn.cursor()
		if ride_time:
			curr.execute("""
				SELECT listing_id, price, username FROM listings
				WHERE ride_date = ? AND ride_time = ?;
				""", (ride_date, ride_time))
		else:
			curr.execute("""
				SELECT listing_id, price, username FROM listings
				WHERE ride_date = ?;
				""", (ride_date,))
		results = curr.fetchall()
		conn.close()

		# if there are any valid listings, append them to the list
		for tup in results:
			driver_username = tup[2]
			# get avg rating of each driver
			data = requests.get(
				"http://user:5000/get_average_rating",
				params={"username": driver_username}
			).json()
			avg = data.get("avg") if data.get("avg") else "0.00"

			listing = {
				"listingid": tup[0],
				"price": f"{tup[1] / 100:.2f}",  # convert to dollars
				"driver": driver_username,
				"rating": avg
			}
			listings.append(listing)
		return json.dumps({"status": 1, "data": listings})

	except Exception:
		logger.exception("Error in search")
		try:
			if conn is not None:
				conn.close()
		except Exception:
			pass
		return json.dumps({"status": 2, "error": "INTERNAL_ERROR", "data": []})


@app.route('/get_driver_price', methods=['GET'])
def get_driver_price() -> str:
	"""Internal helper to return (driver_username, price_cents, ride_date, ride_time) for a listing."""
	listingid = request.args.get("listingid")

	conn: Optional[sqlite3.Connection] = None
	try:
		conn = get_db()
		curr = conn.cursor()

		curr.execute("""
			SELECT username, price, ride_date, ride_time
			FROM listings WHERE listing_id = ?;
			""", (listingid,))
		result = curr.fetchone()
		conn.close()
		if not result:
			return json.dumps({"status": 2, "error": "NOT_FOUND", "data": None})
		return json.dumps({"status": 1, "data": result})

	except Exception:
		logger.exception("Error in get_driver_price")
		try:
			if conn is not None:
				conn.close()
		except Exception:
			pass
		return json.dumps({"status": 2, "error": "INTERNAL_ERROR", "data": None})


@app.route('/remove_availability', methods=['POST'])
def remove_availability() -> str:
	"""Internal helper to delete a listing once a reservation is made."""
	listingid = request.form.get("listingid")

	try:
		conn = get_db()
		curr = conn.cursor()
		curr.execute("""
			DELETE FROM listings WHERE listing_id = ?;
			""", (listingid,))
		conn.commit()
		conn.close()
		return json.dumps({"status": 1})

	except Exception:
		logger.exception("Error in remove_availability")
		try:
			if conn:
				conn.close()
		except Exception:
			pass
		return json.dumps({"status": 2, "error": "INTERNAL_ERROR"})


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000)
