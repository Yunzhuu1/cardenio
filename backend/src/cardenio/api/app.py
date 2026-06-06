"""FastAPI application factory (design.md §2, api.md §1)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cardenio.api.deps import get_store
from cardenio.api.routes import router
from cardenio.gateway.providers.stub import StubLlmGateway
from cardenio.storage.sqlite import create_engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: set up DB engine, stores, gateway."""
    engine = create_engine("sqlite+aiosqlite:///./cardenio.db")
    await init_db(engine)
    app.state.engine = engine
    app.state.gateway = StubLlmGateway()
    app.state.store = get_store(engine)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Cardenio API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router, prefix="/api/v1")
    return app
