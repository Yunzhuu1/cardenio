"""FastAPI application factory (design.md §2, api.md §1)."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from cardenio.api.errors import CardenioError
from cardenio.api.middleware import cardenio_error_handler
from cardenio.api.routes import router
from cardenio.gateway.providers.deepseek import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TIMEOUT_SECONDS,
    DeepSeekGateway,
    DeepSeekGatewayConfig,
)
from cardenio.gateway.providers.stub import StubLlmGateway
from cardenio.storage.sqlite import create_engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Set up DB engine, session factory, gateway on startup."""
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    database_url = os.getenv(
        "CARDENIO_DATABASE_URL", "sqlite+aiosqlite:///./cardenio.db"
    )
    engine = create_engine(database_url)
    await init_db(engine)

    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.gateway = create_gateway_from_env()

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


def create_gateway_from_env() -> StubLlmGateway | DeepSeekGateway:
    """Create the configured LLM gateway.

    Defaults to DeepSeek (LLM mode). Falls back to the local stub gateway when
    no API key is configured so the app always starts; set
    ``CARDENIO_LLM_PROVIDER=stub`` to force stub mode explicitly.
    """
    provider = os.getenv("CARDENIO_LLM_PROVIDER", "deepseek").strip().lower()
    if provider in {"", "stub"}:
        logging.getLogger(__name__).info("LLM gateway: stub (CARDENIO_LLM_PROVIDER=stub)")
        return StubLlmGateway()
    if provider != "deepseek":
        raise ValueError("CARDENIO_LLM_PROVIDER must be 'stub' or 'deepseek'")

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        logging.getLogger(__name__).warning(
            "DEEPSEEK_API_KEY is not set; falling back to StubLlmGateway"
        )
        return StubLlmGateway()

    timeout = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
    gateway = DeepSeekGateway(
        DeepSeekGatewayConfig(
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
            base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL),
            timeout_seconds=timeout,
            max_tokens=max_tokens,
        )
    )
    logging.getLogger(__name__).info(
        "LLM gateway: deepseek (model=%s)", gateway.config.model
    )
    return gateway
