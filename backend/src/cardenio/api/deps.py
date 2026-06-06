"""Dependency injection for FastAPI routes.

Uses ``app.state`` for MVP; swap to proper DI container for production.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from cardenio.gateway.protocol import LlmGateway
from cardenio.storage.protocol import ArtifactStore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def get_gateway(request: Request) -> LlmGateway:
    """Get the LLM gateway from app state."""
    return request.app.state.gateway


def get_store(request: Request) -> ArtifactStore:
    """Get the artifact store from app state (MVP: in-memory or SQLite)."""
    return request.app.state.store


def get_engine(request: Request) -> AsyncEngine:
    """Get the database engine from app state."""
    return request.app.state.engine
