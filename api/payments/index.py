"""
Payments and wallet microservice for the ridedemand project.

This service tracks user balances in cents, supports deposits, and performs
internal transfers between riders and drivers when a reservation is made.
"""

import json
import os
import sqlite3

import requests
from flask import Flask, request

from api.common.auth import get_username_from_jwt, is_valid_jwt

app = Flask(__name__)
db_name = "/tmp/payments.db"
sql_file = "api/payments/payments.sql"
db_flag = False


def create_db():
	"""Create the SQLite database from the SQL schema file if it does not exist."""
	conn = None
	try:
		conn = sqlite3.connect(db_name)
		with open(sql_file, 'r') as sql_startup:
			init_db = sql_startup.read()
		cursor = conn.cursor()
		cursor.executescript(init_db)
		conn.commit()
		global db_flag
		db_flag = True
		return conn
	except Exception as e:
		print("Error in create_db:", e)
		return
	finally:
		if conn is not None:
			conn.close()


def get_db():
	"""Return a SQLite connection, creating the database on first use."""
	if not db_flag:
		create_db()
	conn = sqlite3.connect(db_name)
	curr = conn.cursor()
	curr.execute("PRAGMA foreign_keys = ON;")
	return conn


@app.route('/api/payments/clear', methods=['GET'])
def clear():
	"""Reset the payments database by deleting and recreating the file."""
	if os.path.exists(db_name):
		os.remove(db_name)
	create_db()
	print("Database has been cleared and recreated")
	return "The database has been cleared"

@app.route('/api/payments/init_balance', methods=['POST'])
def init_balance():
	"""Internal endpoint to initialize a new user's starting balance."""
	username = request.form.get("username")
	amount_cents_str = request.form.get("amount_cents")

	try:
		conn = get_db()
		curr = conn.cursor()
		amount_cents = int(amount_cents_str)

		# make sure user doesn't already exist
		curr.execute("""
			SELECT username FROM balances WHERE username = ?;
			""",(username,))
		result = curr.fetchone()
		if result:  # username in database so fail
			conn.close()
			return json.dumps({"status": 2})

		curr.execute("""
			INSERT INTO balances VALUES(?,?);
			""",(username, amount_cents))

		conn.commit()
		conn.close()
		return json.dumps({"status": 1})

	except Exception as e:
		print("Error in init_balance:", e)
		try:
			conn.close()
		except:
			pass

		return json.dumps({"status": 2})


@app.route('/api/payments/add', methods=['POST'])
def add():
	"""Add money to the authenticated user's account if they already exist."""
	amount_str = request.form.get("amount")
	jwt = request.headers.get('Authorization')

	if not is_valid_jwt(jwt):
		return json.dumps({"status": 2})
	username = get_username_from_jwt(jwt)

	try:
		conn = get_db()
		curr = conn.cursor()
		amount_cents = int(float(amount_str) * 100)

		curr.execute("""
			SELECT balance FROM balances WHERE username = ?;
			""",(username,))
		result = curr.fetchone()
		if not result:  # username not in database so fail
			conn.close()
			return json.dumps({"status": 2})
		new_balance = result[0] + amount_cents
		curr.execute("""
			UPDATE balances SET balance = ? WHERE username = ?;
			""",(new_balance, username))

		conn.commit()
		conn.close()
		return json.dumps({"status": 1})

	except Exception as e:
		print("Error in add:", e)
		try:
			conn.close()
		except:
			pass

		return json.dumps({"status": 2})


@app.route('/api/payments/view', methods=['GET'])
def view():
	"""Return the authenticated user's current balance in dollars."""
	jwt = request.headers.get('Authorization')

	if not is_valid_jwt(jwt):
		return json.dumps({"status": 2, "balance": "NULL"})
	username = get_username_from_jwt(jwt)

	try:
_db()
		curr = conn.cursor()

		curr.execute("""
			SELECT balance FROM balances WHERE username = ?;
			""",(username,))
		result = curr.fetchone()
		conn.close()
		if not result:  # username not in database so fail
			return json.dumps({"status": 2, "balance": "NULL"})
		balance = result[0] / 100
		return json.dumps({"status": 1, "balance": f"{balance:.2f}"})

	except Exception as e:
		print("Error in view:", e)
		try:
			conn.close()
		except:
			pass
		return json.dumps({"status": 2, "balance": "NULL"})


@app.route('/api/payments/transfer', methods=['POST'])
def transfer():
	"""
	Internal endpoint: transfer funds from rider to driver if rider has enough.

	Form fields:
	- price_cents: integer price of the ride
	- rider_username
	- driver_username
	"""
	price_cents = int(request.form.get("price_cents"))
	rider_username = request.form.get("rider_username")
	driver_username = request.form.get("driver_username")

	try:
		conn = get_db()
		curr = conn.cursor()

		# check that rider has enough funds
		curr.execute("""
			SELECT balance FROM balances WHERE username = ?;
			""",(rider_username,))
		rider_result = curr.fetchone()
		if not rider_result or rider_result[0] < price_cents:
			conn.close()
			return json.dumps({"status": 2})

		# get drivers balance
		curr.execute("""
					SELECT balance FROM balances WHERE username = ?;
					""", (driver_username,))
		driver_result = curr.fetchone()
		if not driver_result:
			conn.close()
			return json.dumps({"status": 2})

		# subtract funds from rider
		new_balance = rider_result[0] - price_cents
		curr.execute("""
			UPDATE balances SET balance = ? WHERE username = ?;
			""",(new_balance, rider_username))

		# add funds to driver
		new_balance = driver_result[0] + price_cents
		curr.execute("""
				UPDATE balances SET balance = ? WHERE username = ?;
				""", (new_balance, driver_username))

		conn.commit()
		conn.close()
		return json.dumps({"status": 1})

	except Exception as e:
		print("Error in transfer:", e)
		try:
			conn.close()
		except:
			pass
		return json.dumps({"status": 2})
