"""SQLite engine creation and initialization.

SQLite is the default database for MVP.  Can be swapped to PostgreSQL
by changing the engine URL and using the asyncpg driver.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from cardenio.storage.sqlalchemy_models import Base


def create_engine(db_url: str = "sqlite+aiosqlite:///./cardenio.db") -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Default: SQLite with aiosqlite driver, suitable for M0 development.
    For production, swap to ``postgresql+asyncpg://...``.
    """
    return create_async_engine(db_url, echo=False)


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables.  For MVP; use Alembic migrations in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.url.get_backend_name() == "sqlite":
            columns = await conn.execute(text("PRAGMA table_info(projects)"))
            names = {row[1] for row in columns}
            if "deleted_at" not in names:
                await conn.execute(text("ALTER TABLE projects ADD COLUMN deleted_at DATETIME"))
