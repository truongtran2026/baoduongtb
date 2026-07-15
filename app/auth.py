"""Minimal cookie-session authentication - only enforced when the app is
running against a cloud database (see REQUIRE_LOGIN below). The LAN
deployment relies on network access as its security boundary, same as
before; a deployment reachable from the public internet needs a real login
since it now holds real employee/device data (including security equipment)
for anyone with the URL.

Passwords are hashed with PBKDF2 straight from stdlib `hashlib` rather than
a compiled library like bcrypt - one less thing that can fail to build on a
serverless platform's Python runtime.
"""
import hashlib
import hmac
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from .database import IS_SQLITE

PBKDF2_ITERATIONS = 260_000
REQUIRE_LOGIN = not IS_SQLITE

PUBLIC_PATH_PREFIXES = ("/static/",)
PUBLIC_PATHS = {"/login"}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, digest_hex = password_hash.split("$", 1)
    except ValueError:
        return False
    expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return hmac.compare_digest(expected.hex(), digest_hex)


_generated_secret = secrets.token_hex(32)


def get_session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET")
    if secret:
        return secret
    # No SESSION_SECRET set: use a secret generated once at process start.
    # Fine for local/LAN use (nobody needs sessions to survive a restart of
    # a machine they're sitting next to); a real cloud deployment should set
    # SESSION_SECRET explicitly so a redeploy doesn't log everyone out.
    return _generated_secret


class LoginRequiredMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not REQUIRE_LOGIN:
            return await call_next(request)
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PATH_PREFIXES):
            return await call_next(request)
        if not request.session.get("user_id"):
            return RedirectResponse("/login", status_code=303)
        return await call_next(request)
