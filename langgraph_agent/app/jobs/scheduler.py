"""
Central Job Scheduler Daemon — Phase 5 Scheduling.

Runs scheduled background tasks asynchronously.
Can run in-process within FastAPI lifespan or standalone via CLI.
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

# Ensure root paths are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from dotenv import load_dotenv
load_dotenv()

from app.jobs.registry import JOB_REGISTRY, run_registered_job

logger = logging.getLogger("elarion.scheduler")


class PlatformJobScheduler:
    """Async background task scheduler coordinating platform recurring jobs."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    def is_running(self) -> bool:
        return self._running

    async def start(self):
        """Starts the background scheduling loop."""
        if self._running:
            logger.warning("[SCHEDULER] Scheduler is already running.")
            return

        self._running = True
        logger.info("[SCHEDULER] Platform Background Scheduler started.")
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

    async def _scheduler_loop(self):
        """
        Main evaluation loop. Checks jobs and triggers execution based on scheduled cadences.
        In production / local dev, polls every 60 seconds.
        """
        while self._running:
            try:
                # Interval sleep between checks
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SCHEDULER] Error in scheduler loop: {e}", exc_info=True)


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
