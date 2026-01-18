"""
Shared authentication and JWT utilities for the ridedemand microservices.

All services trust the same HMAC signing key so they can validate tokens
issued by the user service.
"""

import base64
import hashlib
import hmac
import json
import logging
import os


logger = logging.getLogger(__name__)


def _get_signing_key() -> bytes:
	"""
	Return the HMAC signing key for JWTs.

	For realism, we first check the JWT_SECRET environment variable and fall
	back to reading from key.txt for local development.
	"""
	secret = os.getenv("JWT_SECRET")
	if secret:
		return secret.encode("utf-8")
	with open("key.txt", "r") as key_file:
		return key_file.read().encode("utf-8")


def get_signature(header_b64: str, payload_b64: str) -> str:
	"""Generate a hexadecimal HMAC-SHA256 signature for a JWT header and payload."""
	key = _get_signing_key()
	hasher = hmac.new(key, digestmod=hashlib.sha256)
	hasher.update(f"{header_b64}.{payload_b64}".encode("utf-8"))
	return hasher.hexdigest()


def generate_jwt(username: str) -> str:
	"""Generate a simple JWT that encodes a username."""
	header_bytes = json.dumps({
		"alg": "HS256",
		"typ": "JWT",
	}).encode("utf-8")

	payload_bytes = json.dumps({
		"username": username,
	}).encode("utf-8")

	header_b64 = base64.urlsafe_b64encode(header_bytes).decode("utf-8")
	payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8")

	signature = get_signature(header_b64, payload_b64)
	return f"{header_b64}.{payload_b64}.{signature}"


def is_valid_jwt(jwt: str, login_username: str | None = None) -> bool:
	"""
	Decode the JWT to validate it.

	If login_username is provided, ensure the token was issued for that username.
	"""
	try:
		if not jwt:
			return False
		jwt_list = jwt.split('.')
		if len(jwt_list) != 3:
			return False
		header_b64 = jwt_list[0]
		payload_b64 = jwt_list[1]
		signature = jwt_list[2]

		real_signature = get_signature(header_b64, payload_b64)
		if signature != real_signature:
			return False

		payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
		payload_dict = json.loads(payload_json)

		if "username" not in payload_dict:
			return False
		if login_username and payload_dict["username"] != login_username:
			return False
		return True
	except Exception:
		logger.exception("Error in is_valid_jwt")
		return False


def get_username_from_jwt(jwt: str) -> str | None:
	"""Extract and return the username from a JWT, or None on error."""
	try:
		jwt_list = jwt.split('.')
		payload_b64 = jwt_list[1]
		payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
		payload_dict = json.loads(payload_json)
		return payload_dict["username"]
	except Exception:
		logger.exception("Error in get_username_from_jwt")
		return None

