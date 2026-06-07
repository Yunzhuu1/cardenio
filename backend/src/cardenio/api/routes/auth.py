"""Authentication API routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from cardenio.api.deps import get_current_user, get_db_session
from cardenio.api.errors import (
    InvalidRequestError,
    UnauthenticatedError,
    VersionConflictError,
)
from cardenio.domain.auth import (
    AuthenticatedUser,
    hash_password,
    hash_token,
    issue_access_token,
    normalize_email,
    token_response,
    verify_password,
)
from cardenio.storage.repository import AuthSessionRepository, UserRepository

router = APIRouter(prefix="/auth")


class RegisterRequest(BaseModel):
    """Register request body."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    display_name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    """Login request body."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


@router.post("/register", status_code=201)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """API-A1: Register an author account and return a login session."""
    email = _validate_email(payload.email)
    _validate_register_password(payload.password)
    users = UserRepository(session)
    if await users.get_by_email(email) is not None:
        raise VersionConflictError("Email is already registered")

    display_name = _clean_display_name(payload.display_name)
    user = await users.create(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=display_name,
    )
    issued = issue_access_token()
    await AuthSessionRepository(session).create(
        user_id=user.id,
        token_hash=issued.token_hash,
        expires_at=issued.expires_at,
    )
    return token_response(
        access_token=issued.access_token,
        expires_at=issued.expires_at,
        user=AuthenticatedUser(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
        ),
    )


@router.post("/login")
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """API-A2: Login with email and password."""
    email = _validate_email(payload.email)
    _validate_login_password(payload.password)
    user = await UserRepository(session).get_by_email(email)
    if (
        user is None
        or user.status != "active"
        or not verify_password(payload.password, user.password_hash)
    ):
        raise UnauthenticatedError("Invalid email or password")

    issued = issue_access_token()
    await AuthSessionRepository(session).create(
        user_id=user.id,
        token_hash=issued.token_hash,
        expires_at=issued.expires_at,
    )
    return token_response(
        access_token=issued.access_token,
        expires_at=issued.expires_at,
        user=AuthenticatedUser(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
        ),
    )


@router.get("/me")
async def me(current_user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """API-A3: Return the current authenticated user."""
    return current_user.to_dict()


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """API-A4: Revoke the current bearer token session."""
    del current_user
    await revoke_current_token(_extract_token(request), session)
    return Response(status_code=204)


async def revoke_current_token(
    access_token: str,
    session: AsyncSession,
) -> None:
    """Revoke an active token if it still exists."""
    await AuthSessionRepository(session).revoke_by_token_hash(
        hash_token(access_token),
        now=datetime.now(UTC),
    )


def _clean_display_name(display_name: str | None) -> str | None:
    if display_name is None:
        return None
    cleaned = display_name.strip()
    if not cleaned:
        return None
    if len(cleaned) > 200:
        raise InvalidRequestError("Display name is too long")
    return cleaned


def _validate_email(email: str) -> str:
    normalized = normalize_email(email)
    if (
        "@" not in normalized
        or normalized.startswith("@")
        or normalized.endswith("@")
        or "." not in normalized.rsplit("@", 1)[1]
    ):
        raise InvalidRequestError("Invalid email address")
    return normalized


def _validate_register_password(password: str) -> None:
    if len(password) < 8 or len(password) > 1024:
        raise InvalidRequestError("Password must be between 8 and 1024 characters")


def _validate_login_password(password: str) -> None:
    if not password or len(password) > 1024:
        raise InvalidRequestError("Invalid password")


def _extract_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    _, _, token = authorization.partition(" ")
    return token.strip()
