import json
import logging
import os
import sqlite3
from typing import Optional

import requests
from flask import Flask, request

from api.common.auth import get_username_from_jwt, is_valid_jwt

logger = logging.getLogger(__name__)

app = Flask(__name__)
db_name = "/tmp/reservations.db"
sql_file = "api/reservations/reservations.sql"
db_flag = False


def create_db() -> None:
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
	if not db_flag:
		create_db()
	conn = sqlite3.connect(db_name)
	curr = conn.cursor()
	curr.execute("PRAGMA foreign_keys = ON;")
	return conn


@app.route('/api/reservations/clear', methods=['GET'])
def clear() -> str:
	if os.path.exists(db_name):
		os.remove(db_name)
	create_db()
	logger.info("Data base has been cleared and recreated")
	return "The database has been cleared"
#
# ALL OF THE ABOVE IS PRETTY MUCH THE SAME FOR EVERY MICRO SERVICE


@app.route('/api/reservations/check_reservation', methods=['GET'])
def check_reservation():
	"""
	Internal func to check if the two users have a reservation togeather
	:return: bool 1 if valid else 0
	"""
	username1 = request.args.get("username1")
	username2 = request.args.get("username2")

	try:
		conn = get_db()
		curr = conn.cursor()

		curr.execute("""
			SELECT * FROM reservations 
			WHERE (driver_username = ? AND rider_username = ?)
			OR (driver_username = ? AND rider_username = ?);
			""",(username1, username2, username2, username1))
		result = curr.fetchone()
		status = 1 if result else 0
		conn.close()
		return json.dumps({"status": status})

	except Exception as e:
		print("Error in check_reservation:", e)
		try:
			conn.close()
		except:
			pass

		return json.dumps({"status": 0})


@app.route('/api/reservations/reserve', methods=['POST'])
def reserve():
	""""""
	listingid = request.form.get("listingid")
	jwt = request.headers.get('Authorization')

	if not is_valid_jwt(jwt):
		return json.dumps({"status": 2})
	rider_username = get_username_from_jwt(jwt)

	try:
		# check that the user is a rider
		rider_result = requests.get(
			f"{request.host_url}/api/users/get_driver_status",
			params={"username": rider_username}
		).json()
		if rider_result.get("driver") != 0:
			return json.dumps({"status": 3})

		# check availability and get driver_username, price, date, and time
		availability_payload = requests.get(
			f"{request.host_url}/api/availability/get_driver_price",
			params={"listingid": listingid}
		).json()
		availability_result = availability_payload.get("data")
		if not availability_result:
			return json.dumps({"status": 3})
		driver_username, price_cents, ride_date, ride_time = availability_result

		# check that user has enough money, if so transfer money to driver
		transfer_result = requests.post(
			f"{request.host_url}/api/payments/transfer",
			data={"price_cents": price_cents,
				  "rider_username": rider_username,
				  "driver_username": driver_username
				  }
		).json().get("status")
		if transfer_result != 1:
			return json.dumps({"status": 3})

		# remove availability
		requests.post(
			f"{request.host_url}/api/availability/remove_availability",
			data={"listingid": listingid}
		)

		# add reservation record (store ride date/time and initial status)
		conn = get_db()
		curr = conn.cursor()
		curr.execute("""
			INSERT INTO reservations (
				listing_id,
				driver_username,
				rider_username,
				ride_date,
				ride_time,
				price,
				status
			) VALUES (?,?,?,?,?,?,?);
			""", (
				listingid,
				driver_username,
				rider_username,
				ride_date,
				ride_time,
				price_cents,
				"CONFIRMED"
			))
		conn.commit()
		conn.close()
		return json.dumps({"status": 1})

	except Exception as e:
		print("Error in reserve:", e)
		try:
			conn.close()
		except:
			pass

		return json.dumps({"status": 3})


@app.route('/api/reservations/view', methods=['GET'])
def view():
	""""""
	jwt = request.headers.get('Authorization')
	if not is_valid_jwt(jwt):
		return json.dumps({"status": 2, "data": "NULL"})
	username = get_username_from_jwt(jwt)

	# find out if driver or rider
	driver_result = requests.get(
		f"{request.host_url}/api/users/get_driver_status",
		params={"username": username}
	).json().get("driver")
	if driver_result == 1:
		column_to_sort_on = "driver_username"
		username_column_for_rating = "rider_username"
	elif driver_result == 0:
		column_to_sort_on = "rider_username"
		username_column_for_rating = "driver_username"
	else:  # failure
		return json.dumps({"status": 2, "data": "NULL"})

	try:
		# get the most recent reservation respective to the user
		conn = get_db()
		curr = conn.cursor()
		curr.execute(f"""
			SELECT listing_id, price, {username_column_for_rating}
			FROM reservations 
			WHERE {column_to_sort_on} = ?
			ORDER BY order_id DESC
			LIMIT 1;
			""",(username,))
		result = curr.fetchone()
		conn.close()
		if not result:
			return json.dumps({"status": 2, "data": "NULL"})
		price = result[1] / 100
		opposite_username = result[2]
		rating_result = requests.get(
			f"{request.host_url}/api/users/get_average_rating",
			params={"username": opposite_username}
		).json().get("avg")
		avg = rating_result if rating_result else "0.00"
		return json.dumps({"status": 1, "data": {
			"listingid": result[0],
			"price": f"{price:.2f}",
			"user": opposite_username,
			"rating": avg
		}})

	except Exception as e:
		print("Error in view:", e)
		try:
			conn.close()
		except:
			pass

		return json.dumps({"status": 2, "data": "NULL"})
