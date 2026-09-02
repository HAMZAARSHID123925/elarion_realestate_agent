"""
One shared, persistent checkpointer for the whole master pipeline backed by PostgreSQL.

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
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set in .env")

_pool = None
_saver = None


async def get_checkpointer():
    """Lazily opens one shared AsyncPostgresSaver pool for the process lifetime.

    Neon PostgreSQL (serverless) drops idle SSL connections after ~5 minutes
    AND free-tier limits total concurrent connections to ~5-8 across all
    clients (API server, email server, whatsapp server may all share the
    same database).  Production settings to survive that:
      - min_size=0   : no connections kept warm; all created on demand
      - max_size=3   : kept low so multiple Elarion processes can share Neon's pool
      - max_idle=120 : cull idle connections after 2 min (well before Neon's 5-min cut)
      - timeout=60   : wait up to 60s for a connection (pipeline can be slow)
      - max_lifetime=300 : recycle connections after 5 min to avoid stale SSL
      - reconnect_timeout=30 : give psycopg_pool 30 s to reconnect before raising
    """
    global _pool, _saver
    if _saver is None:
        logger.info("Connecting persistent AsyncPostgresSaver to PostgreSQL...")

        def _on_reconnect_failed(pool):
            logger.error("AsyncPostgresSaver: all reconnect attempts to PostgreSQL failed — pool degraded.")

        _pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=0,          # never keep idle connections alive (Neon kills them)
            max_size=3,          # Neon free tier limits total connections — stay low
            max_idle=120,        # drop connections idle > 2 min before Neon's 5-min timeout
            timeout=60,          # wait up to 60s for a connection from the pool
            max_lifetime=300,    # recycle connections after 5 min to avoid stale SSL
            reconnect_timeout=30,
            reconnect_failed=_on_reconnect_failed,
            kwargs={"autocommit": True},
            open=False
        )
        await _pool.open()
        _saver = AsyncPostgresSaver(_pool)
        await _saver.setup()
        logger.info("AsyncPostgresSaver connected & verified.")
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

