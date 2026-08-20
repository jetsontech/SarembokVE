"""Signed browser session cookies for the public Sarembok client.

The runtime master token never leaves the server. A browser receives a short-lived,
HttpOnly session cookie signed with a key derived from SAREMBOK_AUTH_TOKEN.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from http import cookies

COOKIE_NAME = "sarembok_session"
TTL_SECONDS = 24 * 60 * 60


def _key(master_token: str) -> bytes:
    return hashlib.sha256(("sarembok-public-session:" + master_token).encode()).digest()


def issue(master_token: str, now: int | None = None) -> str:
    if not master_token:
        raise ValueError("master token is required")
    timestamp = int(time.time() if now is None else now)
    nonce = secrets.token_urlsafe(24)
    payload = f"{timestamp}.{nonce}".encode()
    signature = hmac.new(_key(master_token), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + signature).decode().rstrip("=")


def validate(token: str, master_token: str, now: int | None = None) -> bool:
    if not token or not master_token:
        return False
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        timestamp_raw, nonce, signature = raw.split(b".", 2)
        timestamp = int(timestamp_raw)
        if len(nonce) < 16:
            return False
        current = int(time.time() if now is None else now)
        if timestamp > current + 60 or current - timestamp > TTL_SECONDS:
            return False
        payload = timestamp_raw + b"." + nonce
        expected = hmac.new(_key(master_token), payload, hashlib.sha256).digest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def extract_cookie(header: str | None) -> str:
    if not header:
        return ""
    jar = cookies.SimpleCookie()
    try:
        jar.load(header)
        return jar[COOKIE_NAME].value if COOKIE_NAME in jar else ""
    except cookies.CookieError:
        return ""


def cookie_header(token: str) -> str:
    return (
        f"{COOKIE_NAME}={token}; Path=/; Max-Age={TTL_SECONDS}; "
        "HttpOnly; Secure; SameSite=Lax"
    )
