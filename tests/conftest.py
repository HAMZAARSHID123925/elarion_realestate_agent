"""
Pytest configuration and event loop policy setup for Windows & psycopg async mode.
"""
import sys
import asyncio
import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture(scope="session", autouse=True)
def event_loop_policy():
    if sys.platform == "win32":
        policy = asyncio.WindowsSelectorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        return policy
    return asyncio.get_event_loop_policy()
