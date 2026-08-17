"""
Job Runner, Retry Engine & Dead-Letter Sink — Phase 5 Production Scheduling.

Coordinates job execution with:
  1. PostgreSQL Distributed Advisory Locking (prevents multi-worker overlap)
  2. Retries with exponential backoff for transient failures
  3. Execution Telemetry & Timing
  4. Durable PostgreSQL Dead-Letter Sink & Failure Alerts
"""
import time
import asyncio
import inspect
import logging
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional

from app.jobs.locks import job_lock_manager, JobAlreadyRunningError
from app.jobs.alerts import alert_service
from database.dead_letter_repository import dead_letter_repository

logger = logging.getLogger(__name__)


class JobRunner:
    """Executes platform background jobs with distributed locking, retries, and durable DLQ persistence."""

    def __init__(self):
        self._job_telemetry: Dict[str, Dict[str, Any]] = {}

    async def execute_job(
        self,
        job_name: str,
        job_fn: Callable,
        max_retries: int = 2,
        initial_backoff: float = 0.5,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Executes a background job with concurrency locking, retries, and durable DLQ recording.
        """
        start_time = time.perf_counter()
        started_at = datetime.utcnow().isoformat()
        attempts = 0
        last_error = None

        try:
            async with job_lock_manager.acquire(job_name):
                while attempts <= max_retries:
                    attempts += 1
                    try:
                        logger.info(f"[JOB RUNNER] Starting '{job_name}' (Attempt {attempts}/{max_retries + 1})")

                        if inspect.iscoroutinefunction(job_fn):
                            result = await job_fn(*args, **kwargs)
                        else:
                            result = await asyncio.to_thread(job_fn, *args, **kwargs)

                        duration_ms = (time.perf_counter() - start_time) * 1000

                        telemetry = {
                            "job_name": job_name,
                            "status": "SUCCESS",
                            "attempts": attempts,
                            "started_at": started_at,
                            "finished_at": datetime.utcnow().isoformat(),
                            "duration_ms": round(duration_ms, 2),
                            "result_summary": result if isinstance(result, dict) else str(result),
                            "error": None
                        }
                        self._job_telemetry[job_name] = telemetry
                        logger.info(f"[JOB RUNNER] Job '{job_name}' completed successfully in {duration_ms:.2f}ms")
                        return telemetry

                    except Exception as exc:
                        last_error = exc
                        logger.warning(
                            f"[JOB RUNNER] Attempt {attempts} for job '{job_name}' failed: {exc}",
                            exc_info=True
                        )
                        if attempts <= max_retries:
                            backoff_seconds = initial_backoff * (2 ** (attempts - 1))
                            logger.info(f"[JOB RUNNER] Retrying '{job_name}' in {backoff_seconds:.2f}s...")
                            await asyncio.sleep(backoff_seconds)

                # All retries exhausted -> Persist to Durable PostgreSQL Dead-Letter Sink
                duration_ms = (time.perf_counter() - start_time) * 1000
                failed_at = datetime.utcnow().isoformat()

                dlq_record = await dead_letter_repository.create_dead_letter_record(
                    job_name=job_name,
                    attempts=attempts,
                    error_type=type(last_error).__name__ if last_error else "UnknownError",
                    error_message=str(last_error),
                    duration_ms=duration_ms,
                    started_at=started_at,
                    failed_at=failed_at,
                    payload={"args": args, "kwargs": kwargs}
                )
                self._job_telemetry[job_name] = dlq_record

                # Dispatch Dead-Letter Alert
                alert_service.send_dead_letter_alert(
                    job_name=job_name,
                    error_message=str(last_error),
                    attempts=attempts,
                    context={"duration_ms": duration_ms}
                )

                logger.error(
                    f"[JOB RUNNER] Job '{job_name}' failed all {attempts} attempts and was saved to Dead-Letter Sink (ID: {dlq_record.get('dead_letter_id')})."
                )
                return dlq_record

        except JobAlreadyRunningError:
            logger.warning(f"[JOB RUNNER] Job '{job_name}' is already running. Execution rejected.")
            return {
                "job_name": job_name,
                "status": "SKIPPED_ALREADY_RUNNING",
                "message": f"Job '{job_name}' is currently locked by another worker."
            }

    def get_telemetry(self, job_name: Optional[str] = None) -> Any:
        """Returns execution telemetry for a specific job or all registered jobs."""
        if job_name:
            return self._job_telemetry.get(job_name)
        return list(self._job_telemetry.values())

    async def get_dead_letter_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent records from durable dead-letter storage."""
        return await dead_letter_repository.list_dead_letter_records(limit=limit)

    def clear_state(self) -> None:
        """Clears telemetry and test fallback records."""
        self._job_telemetry.clear()
        dead_letter_repository.clear_fallback()


# Shared singleton job runner
job_runner = JobRunner()
