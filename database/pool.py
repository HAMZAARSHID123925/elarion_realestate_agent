"""
Central PostgreSQL Connection Pool — Shared across all database repositories.

Tailored for Neon PostgreSQL (serverless):
  - min_size=0   : never keep idle connections alive (Neon terminates them after 5 min)
  - max_size=5   : capped to prevent connection exhaustion across API/agent processes
  - max_idle=120 : prune connections idle > 2 minutes
  - timeout=60   : connection acquisition timeout
  - max_lifetime=300 : recycle connections after 5 minutes to avoid stale SSL handshakes
"""
import os
import sys
import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

import psycopg
from psycopg_pool import AsyncConnectionPool

# Ensure environment variables are loaded
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for env_path in [os.path.join(root_dir, ".env"), os.path.join(root_dir, "langgraph_agent", ".env")]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
load_dotenv()

logger = logging.getLogger("database.pool")

_pool: Optional[AsyncConnectionPool] = None
_lock = asyncio.Lock()


def get_database_url() -> str:
    """Returns DATABASE_URL from environment or raises RuntimeError."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


async def get_db_pool() -> AsyncConnectionPool:
    """Lazily initializes and returns the shared AsyncConnectionPool singleton."""
    global _pool
    if _pool is None:
        async with _lock:
            if _pool is None:
                db_url = get_database_url()
                logger.info("Initializing shared AsyncConnectionPool for PostgreSQL...")

                def _on_reconnect_failed(p):
                    logger.error("AsyncConnectionPool: all reconnect attempts failed — pool degraded.")

                pool = AsyncConnectionPool(
                    conninfo=db_url,
                    min_size=0,
                    max_size=5,
                    max_idle=120,
                    timeout=60,
                    max_lifetime=300,
                    reconnect_timeout=30,
                    reconnect_failed=_on_reconnect_failed,
                    open=False
                )
                await pool.open()
                _pool = pool
                logger.info("Shared AsyncConnectionPool successfully opened and ready.")
    return _pool


@asynccontextmanager
async def get_db_connection(db_url: Optional[str] = None):
    """
    Async context manager yielding a pooled PostgreSQL connection.
    If a custom db_url is provided (different from system default),
    opens a direct connection and closes it on exit.
    """
    default_url = os.getenv("DATABASE_URL")
    if db_url and db_url != default_url:
        # Fallback to direct connection for custom target URL (e.g. test isolation)
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            yield conn
    else:
        try:
            pool = await get_db_pool()
            async with pool.connection() as conn:
                yield conn
        except Exception as e:
            logger.warning(f"Failed to acquire connection from pool: {e}. Falling back to direct connection.")
            target_url = db_url or get_database_url()
            async with await psycopg.AsyncConnection.connect(target_url) as conn:
                yield conn


async def close_db_pool():
    """Gracefully closes the shared database connection pool on shutdown."""
    global _pool
    if _pool is not None:
        async with _lock:
            if _pool is not None:
                await _pool.close()
                _pool = None
                logger.info("Shared AsyncConnectionPool closed.")
