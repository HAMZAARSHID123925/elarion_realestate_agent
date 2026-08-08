"""
Layer 1: Email Input Channel Launcher (Resend Webhook API).
Primary implementation lives in input_channels/email_server.py.
"""
import sys
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from input_channels.email_server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
