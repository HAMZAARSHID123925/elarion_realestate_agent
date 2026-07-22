"""
One shared, persistent checkpointer for the whole master pipeline.

Why this exists: maintenance/graph.py's human_approval_node pauses execution
with LangGraph's interrupt() and waits for a human decision. That pause/resume
is only durable if the checkpointer backing it is durable too. The old
per-subgraph MemorySaver() lived only in process RAM -- a server restart while
a ticket was mid-approval silently lost it, with no error and no trace.

AsyncSqliteSaver is used here (not AsyncPostgresSaver) because it needs zero
new infrastructure -- you already have SQLite (elarion.db) in this stack, and
CHECKPOINT_DB_PATH just points at another local SQLite file dedicated to
checkpoints. Swap to AsyncPostgresSaver + DATABASE_URL later when Elarion
moves to a shared Postgres deployment -- nothing else in app/pipeline.py or
app/department_nodes.py needs to change, they only depend on get_checkpointer()
returning *some* BaseCheckpointSaver.

One instance is opened lazily and reused for the lifetime of the process --
do not call AsyncSqliteSaver.from_conn_string(...) more than once per process,
each call opens its own SQLite connection.
"""
import os
import logging

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = logging.getLogger(__name__)

CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "checkpoints.db")

_saver_cm = None
_saver = None


async def get_checkpointer():
    """Lazily opens one shared AsyncSqliteSaver for the process lifetime."""
    global _saver_cm, _saver
    if _saver is None:
        logger.info(f"Opening persistent checkpointer at {CHECKPOINT_DB_PATH}")
        _saver_cm = AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)
        _saver = await _saver_cm.__aenter__()
    return _saver


async def close_checkpointer():
    """Call this on app shutdown (FastAPI lifespan / CLI harness exit) to close
    the SQLite connection cleanly."""
    global _saver_cm, _saver
    if _saver_cm is not None:
        await _saver_cm.__aexit__(None, None, None)
        _saver_cm = None
        _saver = None
        logger.info("Persistent checkpointer closed")
