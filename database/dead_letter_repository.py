"""
Dead-Letter Repository — Phase 5 Production Persistence.

Canonical PostgreSQL data access for Dead-Letter job failure records.
Uses async psycopg with row_factory=dict_row.
Connects via DATABASE_URL with resilient in-memory fallback for offline/test environments.
"""
import os
import re
import uuid
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Ensure root directories are loaded
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for env_path in [os.path.join(root_dir, ".env"), os.path.join(root_dir, "langgraph_agent", ".env")]:
    if os.path.exists(env_path):
        load_dotenv(env_path)

load_dotenv()

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = [
    re.compile(r"passw(or)?d", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"auth(orization)?", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
    re.compile(r"credit[_-]?card", re.IGNORECASE)
]


def sanitize_payload(data: Any) -> str:
    """
    Recursively scrubs sensitive keys and credentials before persistence.
    """
    def _scrub(obj: Any) -> Any:
        if isinstance(obj, dict):
            clean = {}
            for k, v in obj.items():
                if any(p.search(str(k)) for p in SENSITIVE_PATTERNS):
                    clean[k] = "[REDACTED_SECRET]"
                else:
                    clean[k] = _scrub(v)
            return clean
        elif isinstance(obj, list):
            return [_scrub(item) for item in obj]
        elif isinstance(obj, str):
            if any(p.search(obj) for p in SENSITIVE_PATTERNS):
                return "[REDACTED_SECRET]"
            return obj
        return obj

    try:
        if isinstance(data, (dict, list)):
            return json.dumps(_scrub(data), default=str)
        return str(data)
    except Exception:
        return "[UNSERIALIZABLE_PAYLOAD]"


def get_db_url() -> Optional[str]:
    return os.getenv("DATABASE_URL")


class DeadLetterRepository:
    """Canonical PostgreSQL repository for Dead-Letter Job records."""

    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url
        self._fallback_memory: List[Dict[str, Any]] = []

    def _url(self) -> Optional[str]:
        return self._db_url if self._db_url is not None else get_db_url()

    async def create_dead_letter_record(
        self,
        job_name: str,
        attempts: int,
        error_type: str,
        error_message: str,
        duration_ms: float = 0.0,
        started_at: Optional[str] = None,
        failed_at: Optional[str] = None,
        payload: Any = None,
        dead_letter_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Persists a permanent job failure record to PostgreSQL with sanitization.
        Falls back to in-memory store if DB is offline.
        """
        dl_id = dead_letter_id or f"DLQ-{uuid.uuid4().hex[:8].upper()}"
        sanitized_summary = sanitize_payload(payload) if payload is not None else None
        now_iso = datetime.utcnow().isoformat()
        st_at = started_at or now_iso
        fl_at = failed_at or now_iso

        record = {
            "dead_letter_id": dl_id,
            "job_name": job_name,
            "status": "DEAD_LETTER",
            "attempts": attempts,
            "error_type": error_type,
            "error_message": error_message,
            "payload_summary": sanitized_summary,
            "duration_ms": round(float(duration_ms), 2),
            "started_at": st_at,
            "failed_at": fl_at,
            "created_at": now_iso
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
                            INSERT INTO dead_letter_jobs (
                                dead_letter_id, job_name, status, attempts,
                                error_type, error_message, payload_summary,
                                duration_ms, started_at, failed_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *;
                            """,
                            (
                                dl_id, job_name, "DEAD_LETTER", attempts,
                                error_type, error_message, sanitized_summary,
                                record["duration_ms"], st_at, fl_at
                            )
                        )
                        row = await cur.fetchone()
                        await conn.commit()
                        if row:
                            return dict(row)
            except Exception as e:
                logger.warning(f"Could not persist DLQ record to PostgreSQL ({e}). Using in-memory fallback.")

        # Fallback to in-memory store
        self._fallback_memory.append(record)
        return record

    async def list_dead_letter_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves recent dead-letter records from PostgreSQL or in-memory fallback.
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
                            SELECT dead_letter_id, job_name, status, attempts,
                                   error_type, error_message, payload_summary,
                                   duration_ms, started_at, failed_at, created_at
                            FROM dead_letter_jobs
                            ORDER BY failed_at DESC
                            LIMIT %s;
                            """,
                            (limit,)
                        )
                        rows = await cur.fetchall()
                        return [dict(r) for r in rows]
            except Exception as e:
                logger.warning(f"Could not read DLQ records from PostgreSQL ({e}). Using in-memory fallback.")

        return list(reversed(self._fallback_memory[-limit:]))

    async def get_dead_letter_by_id(self, dead_letter_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single dead-letter record by ID.
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
                            SELECT dead_letter_id, job_name, status, attempts,
                                   error_type, error_message, payload_summary,
                                   duration_ms, started_at, failed_at, created_at
                            FROM dead_letter_jobs
                            WHERE dead_letter_id = %s;
                            """,
                            (dead_letter_id,)
                        )
                        row = await cur.fetchone()
                        if row:
                            return dict(row)
            except Exception as e:
                logger.warning(f"Could not query DLQ record from PostgreSQL ({e}). Using in-memory fallback.")

        for r in self._fallback_memory:
            if r["dead_letter_id"] == dead_letter_id:
                return r
        return None

    def clear_fallback(self) -> None:
        """Clears in-memory fallback records (for testing)."""
        self._fallback_memory.clear()


# Shared singleton instance
dead_letter_repository = DeadLetterRepository()
