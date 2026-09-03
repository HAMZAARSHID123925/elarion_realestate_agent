"""
Layer 1: Gmail Input Channel Launcher (Free Direct IMAP & SMTP).
Monitors the configured Gmail inbox (e.g. apiusage92@gmail.com), passes tenant emails
through the LangGraph pipeline with conversational state memory, and dispatches threaded replies.
"""
import sys
import asyncio
import logging

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from input_channels.gmail_service import gmail_service

logger = logging.getLogger("GmailLauncher")


def main():
    try:
        asyncio.run(gmail_service.start())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested via KeyboardInterrupt.")


if __name__ == "__main__":
    main()
