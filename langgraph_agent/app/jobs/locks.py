"""
Job Locking & Concurrency Control — Phase 5 Distributed Advisory Locking.

Provides multi-worker and multi-instance mutual exclusion for background jobs using
PostgreSQL 64-bit session-level advisory locks (`pg_try_advisory_lock` / `pg_advisory_unlock`).
Falls back safely to in-memory asyncio locks when database is unconfigured/offline.
"""
import os
import struct
import hashlib
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Optional

import psycopg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_db_url() -> Optional[str]:
    return os.getenv("DATABASE_URL")


def job_name_to_lock_id(job_name: str) -> int:
    """
    Computes a deterministic signed 64-bit integer lock ID from job_name for PostgreSQL bigint advisory locks.
    Range: [-2^63, 2^63 - 1].
    """
    digest = hashlib.sha256(job_name.encode("utf-8")).digest()
    return struct.unpack(">q", digest[:8])[0]


class JobAlreadyRunningError(Exception):
    """Raised when a background job is already executing and locked by another worker/process."""
    def __init__(self, job_name: str):
        super().__init__(f"Job '{job_name}' is currently running and locked.")
        self.job_name = job_name


class JobLockManager:
    """
    Manages distributed concurrency locks using PostgreSQL session-level advisory locks
    with process-local mutex and offline fallback.
    """

    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url
        self._local_locks: Dict[str, asyncio.Lock] = {}
        self._active_jobs: Dict[str, bool] = {}
        self._master_lock = asyncio.Lock()

    def _url(self) -> Optional[str]:
        return self._db_url if self._db_url is not None else get_db_url()

    async def _get_local_lock(self, job_name: str) -> asyncio.Lock:
        async with self._master_lock:
            if job_name not in self._local_locks:
                self._local_locks[job_name] = asyncio.Lock()
            return self._local_locks[job_name]

    def is_locked(self, job_name: str) -> bool:
        """Returns True if the job is locked locally in this process."""
        return self._active_jobs.get(job_name, False)

    @asynccontextmanager
    async def acquire(self, job_name: str, timeout: float = 0.0):
        """
        Attempts to acquire a distributed advisory lock for job_name.
        Guarantees that the lock is held on a dedicated PostgreSQL connection and released on the same connection.
        """
        local_lock = await self._get_local_lock(job_name)

        # 1. Process-local non-blocking acquisition
        if local_lock.locked():
            logger.warning(f"[JOB LOCK] Job '{job_name}' is already running locally in this process.")
            raise JobAlreadyRunningError(job_name)

        await local_lock.acquire()

        db_conn = None
        pg_locked = False
        lock_id = job_name_to_lock_id(job_name)
        db_url = self._url()

        # 2. PostgreSQL Distributed Advisory Lock
        if db_url:
            try:
                # Fast timeout for connection attempt if DB is unreachable
                db_conn = await asyncio.wait_for(
                    psycopg.AsyncConnection.connect(db_url),
                    timeout=1.0
                )
                async with db_conn.cursor() as cur:
                    await cur.execute("SELECT pg_try_advisory_lock(%s);", (lock_id,))
                    row = await cur.fetchone()
                    pg_locked = bool(row and row[0])

                if not pg_locked:
                    logger.warning(f"[JOB LOCK] Job '{job_name}' is locked by another distributed worker (PostgreSQL lock_id={lock_id}).")
                    await db_conn.close()
                    db_conn = None
                    local_lock.release()
                    raise JobAlreadyRunningError(job_name)

                logger.info(f"[JOB LOCK] Acquired PostgreSQL distributed advisory lock for '{job_name}' (lock_id={lock_id})")

            except (psycopg.Error, asyncio.TimeoutError, OSError) as e:
                logger.warning(f"[JOB LOCK] Could not establish PostgreSQL advisory lock for '{job_name}' ({e}). Using local lock fallback.")
                if db_conn:
                    try:
                        await db_conn.close()
                    except Exception:
                        pass
                    db_conn = None

        self._active_jobs[job_name] = True
        try:
            yield
        finally:
            self._active_jobs[job_name] = False

            # Release PostgreSQL advisory lock on the exact same connection
            if db_conn and pg_locked:
                try:
                    async with db_conn.cursor() as cur:
                        await cur.execute("SELECT pg_advisory_unlock(%s);", (lock_id,))
                    logger.info(f"[JOB LOCK] Released PostgreSQL distributed advisory lock for '{job_name}' (lock_id={lock_id})")
                except Exception as e:
                    logger.error(f"[JOB LOCK] Error releasing advisory lock for '{job_name}': {e}")
                finally:
                    try:
                        await db_conn.close()
                    except Exception:
                        pass

            # Release local process lock
            if local_lock.locked():
                local_lock.release()


# Singleton lock manager
job_lock_manager = JobLockManager()
