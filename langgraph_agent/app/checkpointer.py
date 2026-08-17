"""
One shared, persistent checkpointer for the whole master pipeline backed by PostgreSQL,
with MemorySaver fallback for testing or environments where postgres checkpointer is absent.

Why this exists: maintenance/graph.py's human_approval_node pauses execution
with LangGraph's interrupt() and waits for a human decision. That pause/resume
is durable because the checkpointer backing it persists state directly to
Neon PostgreSQL.

AsyncPostgresSaver + DATABASE_URL is used across all input channels and subgraphs.
"""
import os
import sys
import asyncio
import logging

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

try:
    from psycopg_pool import AsyncConnectionPool
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
except ImportError:
    AsyncConnectionPool = None
    AsyncPostgresSaver = None

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None
_saver = None


async def get_checkpointer():
    """Lazily opens one shared AsyncPostgresSaver pool for the process lifetime,
    falling back to MemorySaver if postgres checkpointer is unavailable."""
    global _pool, _saver
    if _saver is None:
        if AsyncPostgresSaver is not None and AsyncConnectionPool is not None and DATABASE_URL:
            try:
                logger.info("Connecting persistent AsyncPostgresSaver to PostgreSQL...")
                _pool = AsyncConnectionPool(
                    conninfo=DATABASE_URL,
                    max_size=10,
                    kwargs={"autocommit": True},
                    open=False
                )
                await _pool.open()
                _saver = AsyncPostgresSaver(_pool)
                await _saver.setup()
                logger.info("AsyncPostgresSaver connected & verified.")
                return _saver
            except Exception as e:
                logger.warning(f"Failed to connect AsyncPostgresSaver: {e}. Falling back to MemorySaver.")
        logger.info("Using MemorySaver checkpointer.")
        _saver = MemorySaver()
    return _saver


async def close_checkpointer():
    """Call this on app shutdown (FastAPI lifespan / CLI harness exit) to close
    the PostgreSQL connection pool cleanly."""
    global _pool, _saver
    if _pool is not None:
        await _pool.close()
        _pool = None
        _saver = None
        logger.info("Persistent AsyncPostgresSaver connection pool closed")
