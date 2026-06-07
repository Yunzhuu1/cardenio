"""Authentication helpers for first-party login."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210_000
TOKEN_BYTES = 32
ACCESS_TOKEN_TTL = timedelta(hours=12)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Current authenticated user principal."""

    id: str
    email: str
    display_name: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
        }


@dataclass(frozen=True)
class IssuedToken:
    """Newly issued bearer token."""

    access_token: str
    token_hash: str
    expires_at: datetime


def normalize_email(email: str) -> str:
    """Normalize email for account lookup."""
    return email.strip().lower()


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against the stored hash string."""
    try:
        scheme, iterations_raw, salt, expected = password_hash.split("$", 3)
        iterations = int(iterations_raw)
    except ValueError:
        return False
    if scheme != PASSWORD_SCHEME:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        iterations,
    ).hex()
    return hmac.compare_digest(digest, expected)


def issue_access_token(*, now: datetime | None = None) -> IssuedToken:
    """Create a bearer token and its server-side hash."""
    issued_at = now or datetime.now(UTC)
    access_token = secrets.token_urlsafe(TOKEN_BYTES)
    return IssuedToken(
        access_token=access_token,
        token_hash=hash_token(access_token),
        expires_at=issued_at + ACCESS_TOKEN_TTL,
    )


def hash_token(access_token: str) -> str:
    """Hash a bearer token for storage and lookup."""
    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()


def token_response(
    *,
    access_token: str,
    expires_at: datetime,
    user: AuthenticatedUser,
) -> dict:
    """Build the API auth response envelope."""
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "user": user.to_dict(),
    }
