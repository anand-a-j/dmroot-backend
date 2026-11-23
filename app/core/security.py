"""
Security utilities: Argon2id passwords, JWT access tokens, opaque refresh tokens.
"""

import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings
from app.core.constants import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.core.exceptions import UnauthorizedException

# ---------------------------------------------------------------------------
# Passwords (Argon2id)
# ---------------------------------------------------------------------------

# argon2-cffi's PasswordHasher uses Argon2id with safe defaults.
_hasher = PasswordHasher()

# Hashing is deliberately slow (CPU heavy). Running it in a thread keeps the
# async event loop free, so one login doesn't freeze every other request.


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hasher.hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    try:
        return await asyncio.to_thread(_hasher.verify, password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True if the stored hash uses outdated parameters (rehash after a successful login)."""
    return _hasher.check_needs_rehash(password_hash)


# Used when the email doesn't exist, so "unknown email" takes as long as
# "wrong password" and attackers can't discover which emails are registered.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing-only")


async def verify_dummy_password(password: str) -> None:
    await verify_password(password=password, password_hash=_DUMMY_HASH)


def validate_password_strength(password: str) -> str:
    """Raise ValueError if weak. Meant to be called inside Pydantic validators."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one letter and one number")
    return password



# Access tokens (JWT, short-lived)

ACCESS_TOKEN_TYPE = "access"


def create_access_token(user_id: UUID) -> str:
    """Claims: user id only. Role and organization are read from the database
    on every request, so changes take effect immediately."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        claims,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> UUID:
    """Validate signature, expiry and claims; return the user id or raise 401."""
    try:
        claims = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Access token has expired") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid access token") from None

    if claims.get("type") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedException("Invalid access token")

    try:
        return UUID(claims["sub"])
    except (ValueError, TypeError):
        raise UnauthorizedException("Invalid access token") from None



# Refresh tokens (opaque random strings, only the hash is stored in the DB)

def generate_refresh_token() -> str:
    """Cryptographically secure random token (~64 chars). Sent to the client once."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """SHA-256 is enough here: the token is already long and random, so unlike
    passwords there is nothing to brute-force. It also lets us look up by hash."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(
        days=settings.refresh_token_expire_days
    )