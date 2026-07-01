import asyncio
import logging

logger = logging.getLogger(__name__)

class GroqRequestQueue:
    """
    Manages concurrent API requests to Groq to avoid rate limits.
    Implements a semaphore for concurrency capping and exponential backoff for retries.
    """
    def __init__(self, max_concurrent=3):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def call(self, coro_fn, *args, retries=3, **kwargs):
        """
        Executes a coroutine with concurrency limits and retries.
        """
        async with self.semaphore:
            for attempt in range(retries):
                try:
                    return await coro_fn(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:
                        logger.error(f"Groq API call failed after {retries} attempts: {e}")
                        raise
                    
                    backoff_time = 2 ** attempt
                    logger.warning(f"Groq API call failed, retrying in {backoff_time}s... Error: {e}")
                    await asyncio.sleep(backoff_time)

# Global queue instance to be used across nodes
groq_queue = GroqRequestQueue(max_concurrent=3)
