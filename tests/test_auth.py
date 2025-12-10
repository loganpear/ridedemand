import os
import sys
from pathlib import Path

# Ensure project root is on the path so `common` can be imported when tests
# are run from different working directories.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from common.auth import generate_jwt, get_username_from_jwt, is_valid_jwt


def test_generate_and_validate_jwt_round_trip(monkeypatch):
	"""JWT generated for a username should validate and round‑trip the username."""
	monkeypatch.setenv("JWT_SECRET", "test-secret-key")
	username = "alice"

	token = generate_jwt(username)

	assert is_valid_jwt(token)
	assert is_valid_jwt(token, login_username=username)
	assert get_username_from_jwt(token) == username


def test_invalid_jwt_fails_validation(monkeypatch):
	"""Tampering with the token should cause validation to fail."""
	monkeypatch.setenv("JWT_SECRET", "test-secret-key")
	username = "bob"
	token = generate_jwt(username)

	# Corrupt the token by changing the signature
	header, payload, _sig = token.split(".")
	tampered = f"{header}.{payload}.deadbeef"

	# Signature should no longer validate
	assert not is_valid_jwt(tampered)


