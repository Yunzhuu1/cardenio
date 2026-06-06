"""Dependency injection for FastAPI routes."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cardenio.gateway.protocol import LlmGateway
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


def get_artifact_store(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SqliteArtifactStore:
    """Provide a per-request SQLite-backed ArtifactStore."""
    return SqliteArtifactStore(session)


def get_job_store(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SqliteJobStore:
    """Provide a per-request SQLite-backed JobStore."""
    return SqliteJobStore(session)


def get_engine(request: Request) -> AsyncEngine:
    """Get the database engine from app state."""
    return request.app.state.engine
