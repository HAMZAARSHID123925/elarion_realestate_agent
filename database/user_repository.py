import os
import logging
from typing import Optional, Dict, Any
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url

class UserRepository:
    """Repository for managing dashboard user credentials and identity."""

    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> str:
        return self._db_url or get_db_url()

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        query = """
        SELECT user_id, email, password_hash, role, active, created_at, updated_at
        FROM users
        WHERE email = %s
        """
        try:
            db_url = self._url()
            async with await psycopg.AsyncConnection.connect(db_url) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, (email,))
                    row = await cur.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user by email: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        query = """
        SELECT user_id, email, password_hash, role, active, created_at, updated_at
        FROM users
        WHERE user_id = %s
        """
        try:
            db_url = self._url()
            async with await psycopg.AsyncConnection.connect(db_url) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, (user_id,))
                    row = await cur.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user by id: {e}")
            return None

user_repository = UserRepository()
