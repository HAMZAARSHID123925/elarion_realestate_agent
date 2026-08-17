"""
Property Repository — Phase 4 API Layer.

Canonical PostgreSQL data access for Property and Unit entities.
Uses async psycopg with row_factory=dict_row.
Connects via DATABASE_URL.
"""
import os
import logging
from typing import List, Dict, Any, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Ensure root directories are loaded
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for env_path in [os.path.join(root_dir, ".env"), os.path.join(root_dir, "langgraph_agent", ".env")]:
    if os.path.exists(env_path):
        load_dotenv(env_path)

load_dotenv()

logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """Returns DATABASE_URL, raising if not configured."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


class PropertyRepository:
    """Canonical PostgreSQL repository for Properties and Units."""

    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> str:
        return self._db_url or get_db_url()

    async def list_properties(
        self,
        city: Optional[str] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves property listings matching optional filter criteria.
        """
        conditions = []
        params: List[Any] = []

        if city:
            conditions.append("LOWER(city) = LOWER(%s)")
            params.append(city)
        if property_type:
            conditions.append("LOWER(property_type) = LOWER(%s)")
            params.append(property_type)
        if min_price is not None:
            conditions.append("price_lakhs >= %s")
            params.append(min_price)
        if max_price is not None:
            conditions.append("price_lakhs <= %s")
            params.append(max_price)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT property_id, title, address, city, property_type, price_lakhs, created_at
            FROM properties
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s;
        """
        params.append(limit)

        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_property_by_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single property record by ID.
        """
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT property_id, title, address, city, property_type, price_lakhs, created_at
                    FROM properties
                    WHERE property_id = %s;
                    """,
                    (property_id,)
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_property_units(self, property_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all rental units belonging to a property.
        """
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT unit_id, property_id, unit_number, created_at
                    FROM units
                    WHERE property_id = %s
                    ORDER BY unit_number ASC;
                    """,
                    (property_id,)
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


# Shared singleton instance
property_repository = PropertyRepository()
