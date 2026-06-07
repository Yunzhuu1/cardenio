"""FastAPI application factory (design.md §2, api.md §1)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from cardenio.api.errors import CardenioError
from cardenio.api.middleware import cardenio_error_handler
from cardenio.api.routes import router
from cardenio.gateway.providers.stub import StubLlmGateway
from cardenio.storage.sqlite import create_engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Set up DB engine, session factory, gateway on startup."""
    engine = create_engine("sqlite+aiosqlite:///./cardenio.db")
    await init_db(engine)

    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.gateway = StubLlmGateway()

    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Cardenio API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_exception_handler(CardenioError, cardenio_error_handler)
    app.include_router(router, prefix="/api/v1")
    return app
