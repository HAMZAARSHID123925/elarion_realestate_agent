"""
Migration runner for Lease Expiry Tracking (Phase 1, Workflow #4).

Connects to PostgreSQL via DATABASE_URL and runs migration SQL files
from the database/migrations/ directory in filename order.

Usage:
    cd langgraph_agent
    python -m database.migrations.run_migration
"""
import os
import sys
import asyncio
import glob
import logging

from dotenv import load_dotenv

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Try loading .env from project root, then langgraph_agent directory, then default cwd
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env_paths = [
    os.path.join(root_dir, ".env"),
    os.path.join(root_dir, "langgraph_agent", ".env"),
]
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set in .env")


async def run_migrations():
    """Executes all .sql files in the migrations directory, ordered by filename."""
    import psycopg

    migrations_dir = os.path.dirname(__file__)
    sql_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))

    if not sql_files:
        print("No migration files found.")
        return

    print(f"Connecting to database...")
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        for sql_file in sql_files:
            filename = os.path.basename(sql_file)
            print(f"Running migration: {filename}")
            with open(sql_file, "r", encoding="utf-8") as f:
                sql_content = f.read()

            try:
                async with conn.cursor() as cur:
                    await cur.execute(sql_content)
                await conn.commit()
                print(f"  [OK] {filename} applied successfully")
            except Exception as e:
                print(f"  [FAIL] {filename} failed: {e}")
                await conn.rollback()
                raise

    print("All migrations completed successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_migrations())
