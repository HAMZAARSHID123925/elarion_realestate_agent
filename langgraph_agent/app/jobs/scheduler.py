"""
Central Job Scheduler Daemon — Phase 5 Scheduling.

Runs scheduled background tasks asynchronously.
Can run in-process within FastAPI lifespan or standalone via CLI.
Evaluates cadences for registered jobs in app.jobs.registry.
"""
import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Ensure root paths are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from dotenv import load_dotenv
load_dotenv()

from app.jobs.registry import JOB_REGISTRY, run_registered_job

logger = logging.getLogger("elarion.scheduler")

# Job cadences in seconds for background polling evaluation
JOB_INTERVALS_SECONDS: Dict[str, int] = {
    "maintenance_sla_monitor": 3600,       # Hourly monitor
    "rent_reminder_scan": 86400,          # Daily scan (24 hours)
    "lease_expiry_scan": 86400,           # Daily scan (24 hours)
    "renewal_reminder_scan": 86400,       # Daily scan (24 hours)
}


class PlatformJobScheduler:
    """Async background task scheduler coordinating platform recurring jobs."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_run: Dict[str, float] = {}
        self._poll_interval = int(os.getenv("SCHEDULER_POLL_INTERVAL_SECONDS", "60"))

    def is_running(self) -> bool:
        return self._running

    async def start(self):
        """Starts the background scheduling loop."""
        if self._running:
            logger.warning("[SCHEDULER] Scheduler is already running.")
            return

        self._running = True
        logger.info(f"[SCHEDULER] Platform Background Scheduler started (poll interval: {self._poll_interval}s).")
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Gracefully stops the background scheduling loop."""
        if not self._running:
            return

        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[SCHEDULER] Platform Background Scheduler stopped cleanly.")

    async def _evaluate_and_run_due_jobs(self):
        """Checks registered jobs and triggers execution for any whose cadence has elapsed."""
        now = time.time()
        for job_name, job_info in JOB_REGISTRY.items():
            interval = JOB_INTERVALS_SECONDS.get(job_name, 86400)
            last = self._last_run.get(job_name, 0)

            # Check if job is due
            if now - last >= interval:
                logger.info(f"[SCHEDULER] Triggering scheduled job '{job_name}' ({job_info.get('domain')})...")
                self._last_run[job_name] = now
                try:
                    # Execute in background task to avoid blocking evaluation loop
                    asyncio.create_task(self._run_job_safe(job_name))
                except Exception as e:
                    logger.error(f"[SCHEDULER] Failed to spawn job '{job_name}': {e}")

    async def _run_job_safe(self, job_name: str):
        """Runs a registered job and logs the result."""
        try:
            result = await run_registered_job(job_name)
            logger.info(f"[SCHEDULER] Job '{job_name}' completed successfully: {result.get('status')}")
        except Exception as e:
            logger.error(f"[SCHEDULER] Execution error in job '{job_name}': {e}", exc_info=True)

    async def _scheduler_loop(self):
        """
        Main evaluation loop. Checks jobs and triggers execution based on scheduled cadences.
        """
        # Initial short grace delay before first check
        await asyncio.sleep(5)

        while self._running:
            try:
                await self._evaluate_and_run_due_jobs()
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SCHEDULER] Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(10)


# Shared singleton scheduler instance
platform_scheduler = PlatformJobScheduler()


def run_standalone():
    """CLI entrypoint for standalone background worker process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger.info("Starting Elarion Standalone Job Scheduler Worker...")

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(platform_scheduler.start())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received termination signal.")
    finally:
        loop.run_until_complete(platform_scheduler.stop())
        loop.close()


if __name__ == "__main__":
    run_standalone()
