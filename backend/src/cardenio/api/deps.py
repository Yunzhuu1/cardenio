"""Dependency injection for FastAPI routes."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cardenio.api.errors import UnauthenticatedError
from cardenio.domain.auth import AuthenticatedUser, hash_token
from cardenio.gateway.protocol import LlmGateway
from cardenio.storage.repository import AuthSessionRepository, UserRepository
from cardenio.storage.sqlite_store import SqliteArtifactStore, SqliteJobStore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def get_gateway(request: Request) -> LlmGateway:
    """Get the LLM gateway from app state."""
    return request.app.state.gateway


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provide a per-request database session."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    """Resolve the bearer token into the current authenticated user."""
    access_token = _extract_bearer_token(request)
    token_hash = hash_token(access_token)
    auth_sessions = AuthSessionRepository(session)
    auth_session = await auth_sessions.get_active_by_token_hash(
        token_hash,
        now=datetime.now(UTC),
    )
    if auth_session is None:
        raise UnauthenticatedError()

    user = await UserRepository(session).get(auth_session.user_id)
    if user is None or user.status != "active":
        raise UnauthenticatedError()
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
    )


def get_artifact_store(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SqliteArtifactStore:
    """Provide a per-request SQLite-backed ArtifactStore."""
    del request
    return SqliteArtifactStore(
        session,
        current_user_id=current_user.id,
        enforce_owner=True,
    )


def get_job_store(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SqliteJobStore:
    """Provide a per-request SQLite-backed JobStore."""
    del request, current_user
    return SqliteJobStore(session)


def get_engine(request: Request) -> AsyncEngine:
    """Get the database engine from app state."""
    return request.app.state.engine


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthenticatedError()
    return token.strip()
