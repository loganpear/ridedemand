import json
import os
import sqlite3
import hashlib

import requests
from flask import Flask, request

from api.common.auth import generate_jwt, get_username_from_jwt, is_valid_jwt

app = Flask(__name__)
db_name = "/tmp/user.db"
sql_file = "api/users/users.sql"
db_flag = False


def create_db():
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
	if not db_flag:
		create_db()
	conn = sqlite3.connect(db_name)
	curr = conn.cursor()
	curr.execute("PRAGMA foreign_keys = ON;")
	return conn


@app.route('/api/users/clear', methods=['GET'])
def clear():
	if os.path.exists(db_name):
		os.remove(db_name)
	create_db()
	print("Data base has been cleared and recreated")
	return "The database has been cleared"


def is_valid_password(username, password, first_name, last_name):
	""" Helper function to validate password"""
	if not password or len(password) < 8:
		return False

	lower = upper = num = False
	for ch in password:
		if ch.islower():
			lower = True
		if ch.isupper():
			upper = True
		if ch.isdigit():
			num = True
	if not (upper and lower and num):
		return False

	if not first_name or first_name.lower() in password.lower():
		return False
	if not last_name or last_name.lower() in password.lower():
		return False
	if not username or username.lower() in password.lower():
		return False

	return True


def is_reused_password(username, password):
	"""Test if the user has already used password """
	record = get_user_record(username)
	if not record:
		return False
	pre_hashed = (password + record["salt"]).encode("utf-8")
	password_hash = hashlib.sha256(pre_hashed).hexdigest()
	try:
		conn = get_db()
		curr = conn.cursor()

		curr.execute("""
			SELECT password_hash FROM passwords WHERE email_address = (?);
			""", (record["email_address"],))
		previous_hashes = curr.fetchall()
		conn.close()

		for previous_hash_tup in previous_hashes:
			if previous_hash_tup[0] == password_hash:
				return True

	except Exception as e:
		print("Error in is_reused_password:", e)
		try:
			conn.close()
		except:
			pass

	return False


def is_unique_email(suspect_email):
	"""	Tests if the email is not already in the database"""
	try:
		conn = get_db()
		curr = conn.cursor()

		curr.execute("""
			SELECT email_address FROM users WHERE email_address = (?);
			""", (suspect_email,))
		results = curr.fetchall()
		conn.close()

		if not results:
			return True

	except Exception as e:
		print("Error in is_valid_username function:", e)
		try:
			conn.close()
		except:
			pass

	return False


def is_unique_username(suspect_username):
	"""tests if the username is already in the database	"""
	try:
		conn = get_db()
		curr = conn.cursor()

		curr.execute("""
			SELECT username FROM users WHERE username = (?);
			""", (suspect_username,))
		results = curr.fetchall()
		conn.close()

		if not results:
			return True

	except Exception as e:
		print("Error in is_valid_username function:", e)
		try:
			conn.close()
		except:
			pass

	return False


@app.route('/api/users/create_user', methods=['POST'])
def create_user():
	first_name = request.form.get("first_name")
	last_name = request.form.get("last_name")
	username = request.form.get("username")
	email_address = request.form.get("email_address")
	driver_bool = request.form.get("driver")
	deposit = request.form.get("deposit")
	password = request.form.get("password")
	salt = request.form.get("salt")

	# before storing any data, we validate all data
	if not is_unique_username(username):
		status = 2
	elif not is_unique_email(email_address):
		status = 3
	elif not is_valid_password(username, password, first_name, last_name):
		status = 4
	else:
		status = 1

	if status > 1:
		return json.dumps({"status": status, "pass_hash": "NULL"})

	else:  # arguments are valid
		pre_hashed = (password + salt).encode("utf-8")
		password_hash = hashlib.sha256(pre_hashed).hexdigest()

		if driver_bool and driver_bool.lower() == "true":
			driver_int = 1
		else:
			driver_int = 0

		# store user info in the database
		try:
			conn = get_db()
			curr = conn.cursor()

			curr.execute("""
				INSERT INTO users VALUES(?,?,?,?,?,?,?,?);
				""",(email_address, first_name, last_name, username,
					 salt, 0, 0, driver_int))

			curr.execute("""
				INSERT INTO passwords VALUES(?,?,?);
				""", (email_address, password_hash, 1))

			conn.commit()
			conn.close()

			# Add initial deposit
			deposit_int = int(float(deposit) * 100)
			requests.post(
				f"{request.host_url}/api/payments/init_balance",
				data = {"username": username,
						"amount_cents": deposit_int
						}
			)
		except Exception as e:
			print("Error in create_user:", e)
			try:
				conn.close()
			except:
				pass

		return json.dumps({"status": status, "pass_hash": password_hash})


@app.route('/api/users/rate', methods=['POST'])
def rate():
	username_to_rate = request.form.get("username")
	rating_int = int(request.form.get("rating"))
	jwt = request.headers.get('Authorization')

	if not is_valid_jwt(jwt):
		return json.dumps({"status": 2})
	username_acting = get_username_from_jwt(jwt)

	if not username_to_rate or username_acting == username_to_rate:
		return json.dumps({"status": 2})
	if not 0 <= rating_int <= 5:
		return json.dumps({"status": 2})

	try:
		# check that the user has a reservation with the one theire rating
		data = requests.get(
			f"{request.host_url}/api/reservations/check_reservation",
			params={"username1": username_acting, "username2": username_to_rate}
		).json()
		if data.get("status") == 0:
			return json.dumps({"status": 2})
		conn = get_db()
		curr = conn.cursor()

		# ensure user being rated exists
		curr.execute("""
			SELECT rating_sum, rating_count FROM users WHERE username = ?;
			""",(username_to_rate,))
		result = curr.fetchone()
		if not result:  # username not in database so fail
			conn.close()
			return json.dumps({"status": 2})
		new_sum = result[0] + rating_int

		curr.execute("""
			UPDATE users SET rating_sum = ?, rating_count = ?
			WHERE username = ?;
			""",(new_sum, result[1] + 1, username_to_rate))

		conn.commit()
		conn.close()
		return json.dumps({"status": 1})

	except Exception as e:
		print("Error in rate:", e)
		try:
			conn.close()
		except:
			pass

		return json.dumps({"status": 2})


@app.route('/api/users/get_average_rating', methods=['GET'])
def get_average_rating():
	"""Internal funk to get users average rating"""
	username = request.args.get("username")

	try:
		conn = get_db()
		curr = conn.cursor()

		curr.execute("""
			SELECT rating_sum, rating_count FROM users WHERE username = ?;
			""",(username,))
		result = curr.fetchone()
		conn.close()
		if not result:  # username not in database so fail
			return json.dumps({"avg": None})
		elif result[1] == 0:  # ensure 0 instead of divide by 0
			return json.dumps({"avg": "0.00"})
		else:
			avg = f"{result[0] / result[1]:.2f}"
			return json.dumps({"avg": avg})

	except Exception as e:
		print("Error in get_average_rating:", e)
		try:
			conn.close()
		except:
			pass
		return json.dumps({"avg": None})


@app.route('/api/users/get_driver_status', methods=['GET'])
def get_driver_status():
	"""Internal funk to get 1 if user is driver or 0 if not"""
	username = request.args.get("username")

	try:
		conn = get_db()
		curr = conn.cursor()

		curr.execute("""
			SELECT driver FROM users WHERE username = ?;
			""",(username,))
		result = curr.fetchone()
		conn.close()
		if not result:  # username not in database so fail
			return json.dumps({"driver": None})
		else:
			return json.dumps({"driver": result[0]})

	except Exception as e:
		print("Error in get_driver_status:", e)
		try:
			conn.close()
		except:
			pass
		return json.dumps({"driver": None})


@app.route('/api/users/set_driver_status', methods=['POST'])
def set_driver_status():
	"""
	Update the driver's status (1 for driver, 0 for rider) for the authenticated user.
	Requires a valid JWT matching the provided username.
	"""
	username = request.form.get("username")
	driver_bool = request.form.get("driver")
	jwt = request.headers.get('Authorization')

	if not is_valid_jwt(jwt, username):
		return json.dumps({"status": 2})

	if driver_bool and driver_bool.lower() == "true":
		driver_int = 1
	else:
		driver_int = 0

	try:
		conn = get_db()
		curr = conn.cursor()
		curr.execute("""
			UPDATE users SET driver = ? WHERE username = ?;
			""", (driver_int, username))
		conn.commit()
		conn.close()
		return json.dumps({"status": 1})

	except Exception as e:
		print("Error in set_driver_status:", e)
		try:
			conn.close()
		except:
			pass
		return json.dumps({"status": 2})


def password_correct(username, password):
	"""Test if current password in correct"""
	if not password or not username:
		return False

	try:
		conn = get_db()
		curr = conn.cursor()

		# check username is in database
		curr.execute("""
			SELECT email_address, salt FROM users WHERE
			username = (?);
			""", (username,))
		results = curr.fetchall()

		if results:
			# check password is correct
			email_address = results[0][0]
			salt = results[0][1]
			pre_hashed = (password + salt).encode("utf-8")
			password_hash = hashlib.sha256(pre_hashed).hexdigest()
			curr.execute("""
				SELECT password_hash FROM passwords 
				WHERE email_address = (?) and is_current = 1;
				""", (email_address,))
			hash_results = curr.fetchall()

			if hash_results and hash_results[0][0] == password_hash:
				conn.close()
				return True

		conn.close()
	except Exception as e:
		print("Error in password_correct:", e)
		try:
			conn.close()
		except:
			pass

	return False


@app.route('/api/users/login', methods=['POST'])
def login():
	username = request.form.get("username")
	password = request.form.get("password")

	if password_correct(username, password):
		jwt = generate_jwt(username)
		return json.dumps({"status": 1, "jwt": jwt})
	else:
		return json.dumps({"status": 2, "jwt": "NULL"})


def get_user_record(username):
	"""Returns the row of data from users table as a dictionary"""
	try:
		conn = get_db()
		conn.row_factory = sqlite3.Row  # will dictionary format the results
		curr = conn.cursor()
		curr.execute("SELECT * FROM users WHERE username = (?);",
					 (username,))
		results = curr.fetchall()
		conn.close()
		if results:
			return dict(results[0])

	except Exception as e:
		print("Error in get_user_record:", e)
		try:
			conn.close()
		except:
			pass


def update_password(username, password):
	"""
	Set current password to is_current = 0
	Insert new password in the passwords table with is_current = 1
	"""
	record = get_user_record(username)
	if not record:
		return
	pre_hashed = (password + record["salt"]).encode("utf-8")
	new_password_hash = hashlib.sha256(pre_hashed).hexdigest()
	try:
		conn = get_db()
		curr = conn.cursor()

		# set previous password to inactive
		curr.execute("""
			UPDATE passwords SET is_current = 0 WHERE email_address = (?);
		""", (record["email_address"],))

		# insert new password
		curr.execute("""
			INSERT INTO passwords VALUES(?,?,1)
		""", (record["email_address"], new_password_hash))

		conn.commit()
		conn.close()
	except Exception as e:
		print("Error in update_password function:", e)
		try:
			conn.close()
		except:
			pass


def update_username(curr_username, new_username):
	"""Update username in the users table"""
	try:
		conn = get_db()
		curr = conn.cursor()
		curr.execute("""
			UPDATE users SET username = (?) WHERE username = (?);
			""", (new_username, curr_username))
		conn.commit()
		conn.close()

	except Exception as e:
		print("Error in update_username:", e)
		try:
			conn.close()
		except:
			pass


@app.route('/api/users/update', methods=['POST'])
def update():
	curr_username = request.form.get("username")
	new_username = request.form.get("new_username")
	curr_password = request.form.get("password")
	new_password = request.form.get("new_password")
	jwt_post = request.form.get("jwt")

	if not is_valid_jwt(jwt_post, curr_username):
		return json.dumps({"status": 3})

	# get confirmed username from jwt so we know this one's correct
	username_confirmed = get_username_from_jwt(jwt_post)

	if new_username:
		if curr_username == username_confirmed:
			if is_unique_username(new_username):
				update_username(curr_username, new_username)
				return json.dumps({"status": 1})

	elif new_password:
		if password_correct(username_confirmed, curr_password):
			if not is_reused_password(username_confirmed, new_password):
				user = get_user_record(username_confirmed)
				if user:
					if is_valid_password(
								username_confirmed,
								new_password,
								user["first_name"],
								user["last_name"]):
						update_password(username_confirmed, new_password)
						return json.dumps({"status": 1})

	return json.dumps({"status": 2})


@app.route('/api/users/view', methods=['POST'])
def view():
	jwt_post = request.form.get("jwt")
	if not is_valid_jwt(jwt_post):
		return json.dumps({"status": 2, "data": "NULL"})

	username = get_username_from_jwt(jwt_post)
	user = get_user_record(username)
	if not user:
		return json.dumps({"status": 2, "data": "NULL"})
	return json.dumps({
		"status": 1,
		"data": {
			"username": username,
			"email_address": user["email_address"],
			"first_name": user["first_name"],
			"last_name": user["last_name"]
		}
	})
