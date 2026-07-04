"""Minimal admin auth: a single shared password mints an HMAC-signed token.

Stateless (no DB/session store) — the token carries its own expiry and is
verified by signature. Good enough to gate the dashboard for a scaffold;
swap for real per-user accounts + OAuth in production.
"""
from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import Header, HTTPException

from app.config import get_settings

_TTL_SECONDS = 12 * 60 * 60  # 12 hours


def _sign(message: str) -> str:
    secret = get_settings().admin_secret.encode()
    return hmac.new(secret, message.encode(), hashlib.sha256).hexdigest()


def create_token() -> str:
    expiry = str(int(time.time()) + _TTL_SECONDS)
    return f"{expiry}.{_sign(expiry)}"


def verify_token(token: str) -> bool:
    if not token or "." not in token:
        return False
    expiry, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(expiry)):
        return False
    try:
        return int(expiry) > time.time()
    except ValueError:
        return False


def check_password(password: str) -> bool:
    return hmac.compare_digest(password or "", get_settings().admin_password)


def require_admin(authorization: str = Header(default="")) -> None:
    """FastAPI dependency: reject requests without a valid admin bearer token."""
    token = authorization.removeprefix("Bearer ").strip()
    if not verify_token(token):
        raise HTTPException(401, "admin authentication required")
