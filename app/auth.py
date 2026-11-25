"""
Optional single-user password protection (stdlib only).

Disabled when APP_PASSWORD is empty (fine on localhost). When set, every API
route requires a signed session cookie obtained from POST /auth/login.
Tokens are ``<expiry>.<hmac>``; no server-side session store is needed.
"""
from __future__ import annotations

import hashlib
import hmac
import time

SESSION_TTL_SECONDS = 7 * 24 * 3600

# Paths reachable without a session. /media stays public on purpose: the
# Instagram/Facebook Graph API must fetch videos from it without logging in
# (filenames carry a random suffix, so they are not guessable).
PUBLIC_PREFIXES = ("/dashboard", "/media", "/auth", "/health")


def _sign(expiry: int, secret: str, password: str) -> str:
    key = hashlib.sha256(f"{secret}\0{password}".encode()).digest()
    return hmac.new(key, str(expiry).encode(), hashlib.sha256).hexdigest()


def create_token(secret: str, password: str, now: float | None = None) -> str:
    expiry = int((time.time() if now is None else now) + SESSION_TTL_SECONDS)
    return f"{expiry}.{_sign(expiry, secret, password)}"


def verify_token(token: str | None, secret: str, password: str, now: float | None = None) -> bool:
    if not token or "." not in token:
        return False
    expiry_s, _, sig = token.partition(".")
    if not expiry_s.isdigit():
        return False
    expiry = int(expiry_s)
    if expiry < (time.time() if now is None else now):
        return False
    return hmac.compare_digest(sig, _sign(expiry, secret, password))


def password_ok(candidate: str, password: str) -> bool:
    return hmac.compare_digest(candidate.encode(), password.encode())


def is_public_path(path: str) -> bool:
    return path == "/" or any(path == p or path.startswith(p + "/") for p in PUBLIC_PREFIXES)
