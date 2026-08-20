"""
Audit Logging Repository — Phase 6 Security & Hardening.

Persists forensic audit logs of security-sensitive and state-modifying actions
into the PostgreSQL `audit_logs` table.
Uses async psycopg with row_factory=dict_row and in-memory test fallback.
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from database.dead_letter_repository import sanitize_payload

# Ensure root directories are loaded
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for env_path in [os.path.join(root_dir, ".env"), os.path.join(root_dir, "langgraph_agent", ".env")]:
    if os.path.exists(env_path):
        load_dotenv(env_path)

load_dotenv()

logger = logging.getLogger(__name__)


def get_db_url() -> Optional[str]:
    return os.getenv("DATABASE_URL")


class AuditRepository:
    """Canonical PostgreSQL repository for audit logs."""

    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url
        self._fallback_memory: List[Dict[str, Any]] = []

    def _url(self) -> Optional[str]:
        return self._db_url if self._db_url is not None else get_db_url()

    async def create_audit_log(
        self,
        action: str,
        actor: str,
        details: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an audit log record with credential scrubbing.
        """
        # Scrub before and after states
        clean_before = json.loads(sanitize_payload(before_state)) if before_state else None
        clean_after = json.loads(sanitize_payload(after_state)) if after_state else None

        detail_text = details
        if request_id:
            detail_text = f"[{request_id}] {details}"

        now_iso = datetime.utcnow().isoformat()
        record = {
            "log_id": len(self._fallback_memory) + 1,
            "action": action,
            "actor": actor,
            "details": detail_text,
            "before_state": clean_before,
            "after_state": clean_after,
            "timestamp": now_iso
        }

        db_url = self._url()
        if db_url:
            try:
                conn = await asyncio.wait_for(
                    psycopg.AsyncConnection.connect(db_url),
                    timeout=1.0
                )
                async with conn:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute(
                            """
                            INSERT INTO audit_logs (action, details, actor, before_state, after_state)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING *;
                            """,
                            (
                                action,
                                detail_text,
                                actor,
                                json.dumps(clean_before) if clean_before else None,
                                json.dumps(clean_after) if clean_after else None
                            )
                        )
                        row = await cur.fetchone()
                        await conn.commit()
                        if row:
                            return dict(row)
            except Exception as e:
                logger.warning(f"Could not persist audit log to PostgreSQL ({e}). Using in-memory fallback.")

        self._fallback_memory.append(record)
        return record

    async def list_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves recent audit logs.
        """
        db_url = self._url()
        if db_url:
            try:
                conn = await asyncio.wait_for(
                    psycopg.AsyncConnection.connect(db_url),
                    timeout=1.0
                )
                async with conn:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute(
                            """
                            SELECT log_id, action, details, actor, before_state, after_state, timestamp
                            FROM audit_logs
                            ORDER BY timestamp DESC
                            LIMIT %s;
                            """,
                            (limit,)
                        )
                        rows = await cur.fetchall()
                        return [dict(r) for r in rows]
            except Exception as e:
                logger.warning(f"Could not read audit logs from PostgreSQL ({e}). Using in-memory fallback.")

        return list(reversed(self._fallback_memory[-limit:]))

    def clear_fallback(self) -> None:
        """Clears in-memory test fallback logs."""
        self._fallback_memory.clear()


# Shared singleton audit repository
audit_repository = AuditRepository()
