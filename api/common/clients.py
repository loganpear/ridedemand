"""
Shared client utilities for making service-to-service calls.
"""
import os
from typing import Optional


def get_service_base_url(env_var_name: str, default: Optional[str] = None) -> str:
    """
    Return the base URL for a service from an environment variable.

    If the environment variable is not set, it falls back to the provided
    default. This allows services to work in both Docker Compose (with env
    vars) and Vercel (with same-origin URLs).
    """
    url = os.getenv(env_var_name)
    if url:
        return url.rstrip("/")
    if default:
        return default.rstrip("/")
    raise ValueError(f"Service URL env var {env_var_name} not set and no default provided.")
