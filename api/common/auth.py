"""
Shared authentication and JWT utilities for the ridedemand microservices.

All services trust the same HMAC signing key so they can validate tokens
issued by the user service. This implementation uses PyJWT to create and
validate tokens according to industry standards.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

logger = logging.getLogger(__name__)


def _get_signing_key() -> str:
    """
    Return the HMAC signing key for JWTs.

    The key MUST be set in the JWT_SECRET environment variable.
    """
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise ValueError("JWT_SECRET environment variable not set")
    return secret


def generate_jwt(username: str) -> str:
    """
    Generate a JWT that encodes the username and has a 1-hour expiration.

    Claims:
    - sub: username
    - iat: issued at time
    - exp: expiration time
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, _get_signing_key(), algorithm="HS256")


def decode_jwt(token: str, expected_username: Optional[str] = None) -> Optional[dict]:
    """
    Decode and validate a JWT, returning its payload if valid.

    Validation checks:
    - Signature
    - Expiration
    - Username (`sub` claim) if `expected_username` is provided.

    Returns the payload dictionary on success, None on failure.
    """

    try:
        payload = jwt.decode(token, _get_signing_key(), algorithms=["HS256"])
        if expected_username and payload.get("sub") != expected_username:
            logger.warning("JWT 'sub' claim does not match expected username.")
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT received.")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT received.", exc_info=True)
        return None


def get_username_from_jwt(token: str) -> Optional[str]:
    """Extract and return the username from a JWT, or None on error."""
    payload = decode_jwt(token)
    return payload.get("sub") if payload else None

def extract_token_from_header(header: str) -> Optional[str]:
    """Extract the token from an 'Authorization: Bearer <token>' header."""
    if not header or not header.startswith("Bearer "):
        return None
    return header.split(" ")[1]
