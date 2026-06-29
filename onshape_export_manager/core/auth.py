"""Single-owner authentication: password hashing, sessions, and TOTP 2FA.

This module deliberately uses only the Python standard library so it adds no
dependencies and runs efficiently on a Raspberry Pi:

* Passwords are hashed with ``hashlib.scrypt`` (salted, tunable cost).
* Sessions are opaque random tokens; only their SHA-256 hash is stored, so a
  database leak never exposes a live session cookie.
* Optional two-factor authentication implements RFC 6238 TOTP with HMAC-SHA1.

The application is intended for a single owner, so there is exactly one account
(``auth_owner`` row with ``id = 1``). Authentication is only enforced once that
owner has been created — a fresh install is in "setup" mode until then.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from onshape_export_manager.core.logger import APP_LOGGER, get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from onshape_export_manager.core.database import Database

SESSION_COOKIE = "oem_session"
SESSION_TTL = timedelta(hours=12)
REMEMBER_TTL = timedelta(days=30)

# scrypt cost parameters — fast on a Pi, still resistant to brute force.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32

_TOTP_STEP = 30
_TOTP_DIGITS = 6


class AuthError(RuntimeError):
    """Raised for authentication failures that should surface to the user."""


@dataclass(frozen=True, slots=True)
class OwnerInfo:
    """Public (non-secret) information about the owner account."""

    username: str
    totp_enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SessionInfo:
    """A validated session."""

    token_hash: str
    expires_at: datetime
    remember: bool


# -- Password hashing -------------------------------------------------------


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return an encoded scrypt hash of ``password``."""
    if not password:
        raise AuthError("password cannot be empty")
    salt = salt or os.urandom(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
        maxmem=64 * 1024 * 1024,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verification of ``password`` against an encoded hash."""
    try:
        scheme, n, r, p, salt_hex, hash_hex = encoded.split("$")
        if scheme != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
            maxmem=64 * 1024 * 1024,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived, expected)


# -- TOTP (RFC 6238) --------------------------------------------------------


def generate_totp_secret() -> str:
    """Return a new base32 TOTP secret."""
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def totp_code(secret: str, *, at: float | None = None, step: int = _TOTP_STEP, digits: int = _TOTP_DIGITS) -> str:
    """Return the TOTP code for ``secret`` at the given time."""
    counter = int((at if at is not None else time.time()) // step)
    key = _b32decode(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**digits)).zfill(digits)


def verify_totp(secret: str, code: str, *, window: int = 1, at: float | None = None) -> bool:
    """Verify a TOTP ``code``, allowing +/- ``window`` time steps for drift."""
    if not secret or not code:
        return False
    code = code.strip().replace(" ", "")
    now = at if at is not None else time.time()
    for delta in range(-window, window + 1):
        if hmac.compare_digest(totp_code(secret, at=now + delta * _TOTP_STEP), code):
            return True
    return False


def totp_provisioning_uri(secret: str, *, account: str, issuer: str = "Onshape Export Manager") -> str:
    """Return an otpauth:// URI for authenticator apps / QR codes."""
    from urllib.parse import quote

    label = quote(f"{issuer}:{account}")
    return (
        f"otpauth://totp/{label}?secret={secret}"
        f"&issuer={quote(issuer)}&algorithm=SHA1&digits={_TOTP_DIGITS}&period={_TOTP_STEP}"
    )


def _b32decode(secret: str) -> bytes:
    padded = secret.upper() + "=" * (-len(secret) % 8)
    return base64.b32decode(padded)


# -- Auth service -----------------------------------------------------------


class AuthService:
    """Owner account, session, and 2FA management backed by SQLite."""

    def __init__(self, database: "Database") -> None:
        self.db = database
        self.logger = get_logger(APP_LOGGER)

    # -- Owner ----------------------------------------------------------

    def is_configured(self) -> bool:
        """Return True once an owner account exists (auth is then enforced)."""
        with self.db.connect() as conn:
            row = conn.execute("SELECT 1 FROM auth_owner WHERE id = 1").fetchone()
        return row is not None

    def owner_info(self) -> OwnerInfo | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT username, totp_enabled, created_at, updated_at FROM auth_owner WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        return OwnerInfo(
            username=str(row["username"]),
            totp_enabled=bool(row["totp_enabled"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def create_owner(self, username: str, password: str) -> None:
        """Create the single owner account. Fails if one already exists."""
        username = username.strip()
        if not username:
            raise AuthError("username cannot be empty")
        if len(password) < 8:
            raise AuthError("password must be at least 8 characters")
        if self.is_configured():
            raise AuthError("owner account already exists")
        now = _now_iso()
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_owner (id, username, password_hash, totp_secret,
                                        totp_enabled, created_at, updated_at)
                VALUES (1, ?, ?, NULL, 0, ?, ?)
                """,
                (username, hash_password(password), now, now),
            )
        self.logger.info("Owner account created username=%s", username)

    def authenticate(self, username: str, password: str) -> bool:
        """Return True if the username/password match the owner account."""
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT username, password_hash FROM auth_owner WHERE id = 1"
            ).fetchone()
        if row is None:
            return False
        if not hmac.compare_digest(str(row["username"]), username.strip()):
            # Still run the hash to reduce username enumeration timing signal.
            verify_password(password, str(row["password_hash"]))
            return False
        return verify_password(password, str(row["password_hash"]))

    def change_password(self, current: str, new: str) -> None:
        info = self.owner_info()
        if info is None:
            raise AuthError("no owner account configured")
        if not self.authenticate(info.username, current):
            raise AuthError("current password is incorrect")
        self.reset_password(new)

    def reset_password(self, new: str) -> None:
        """Set a new password and invalidate all existing sessions."""
        if len(new) < 8:
            raise AuthError("password must be at least 8 characters")
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE auth_owner SET password_hash = ?, updated_at = ? WHERE id = 1",
                (hash_password(new), _now_iso()),
            )
            conn.execute("DELETE FROM auth_sessions")
        self.logger.warning("Owner password reset; all sessions invalidated")

    # -- TOTP -----------------------------------------------------------

    def totp_enabled(self) -> bool:
        info = self.owner_info()
        return bool(info and info.totp_enabled)

    def begin_totp_enrollment(self) -> str:
        """Generate and store a pending TOTP secret; returns the secret."""
        secret = generate_totp_secret()
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE auth_owner SET totp_secret = ?, totp_enabled = 0, updated_at = ? WHERE id = 1",
                (secret, _now_iso()),
            )
        return secret

    def confirm_totp(self, code: str) -> bool:
        """Confirm enrollment by verifying a code against the pending secret."""
        secret = self._totp_secret()
        if secret is None or not verify_totp(secret, code):
            return False
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE auth_owner SET totp_enabled = 1, updated_at = ? WHERE id = 1",
                (_now_iso(),),
            )
        self.logger.info("TOTP two-factor authentication enabled")
        return True

    def verify_login_totp(self, code: str) -> bool:
        secret = self._totp_secret()
        return bool(secret) and verify_totp(secret, code)

    def disable_totp(self) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE auth_owner SET totp_secret = NULL, totp_enabled = 0, updated_at = ? WHERE id = 1",
                (_now_iso(),),
            )
        self.logger.info("TOTP two-factor authentication disabled")

    def _totp_secret(self) -> str | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT totp_secret FROM auth_owner WHERE id = 1").fetchone()
        return str(row["totp_secret"]) if row and row["totp_secret"] else None

    # -- Sessions -------------------------------------------------------

    def create_session(self, *, remember: bool = False, user_agent: str = "") -> str:
        """Create a session and return the raw token to set as a cookie."""
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        now = _utc_now()
        expires = now + (REMEMBER_TTL if remember else SESSION_TTL)
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_sessions (token_hash, created_at, expires_at, remember, user_agent)
                VALUES (?, ?, ?, ?, ?)
                """,
                (token_hash, now.isoformat(), expires.isoformat(), int(remember), user_agent[:300]),
            )
        return token

    def validate_session(self, token: str | None) -> bool:
        """Return True if the token maps to an unexpired session."""
        if not token:
            return False
        token_hash = _hash_token(token)
        now = _utc_now()
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT expires_at FROM auth_sessions WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        if row is None:
            return False
        return datetime.fromisoformat(row["expires_at"]) > now

    def destroy_session(self, token: str | None) -> None:
        if not token:
            return
        with self.db.connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_hash_token(token),))

    def purge_expired_sessions(self) -> int:
        with self.db.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM auth_sessions WHERE expires_at <= ?", (_utc_now().isoformat(),)
            )
            return cursor.rowcount


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _utc_now().isoformat()
