"""
Property Repository — Phase 4 API Layer + Phase 9 Dashboard Cards.

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
        status: Optional[str] = None,
        search: Optional[str] = None,
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
        if status:
            conditions.append("LOWER(status) = LOWER(%s)")
            params.append(status)
        if search:
            conditions.append("(LOWER(title) LIKE LOWER(%s) OR LOWER(city) LIKE LOWER(%s) OR LOWER(address) LIKE LOWER(%s))")
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT property_id, title, address, city, property_type, price_lakhs,
                   COALESCE(status, 'Active') as status,
                   COALESCE(units_count, 0) as units_count,
                   created_at
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
                    SELECT property_id, title, address, city, property_type, price_lakhs,
                           COALESCE(status, 'Active') as status,
                           COALESCE(units_count, 0) as units_count,
                           created_at
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

    async def create_property(self, data: Dict[str, Any]) -> str:
        """
        Creates a new property record.
        """
        db_url = self._url()
        property_id = data.get("property_id")
        if not property_id:
            import uuid
            property_id = f"P-{uuid.uuid4().hex[:8].upper()}"

        fields = ["property_id", "title", "address", "city", "property_type", "price_lakhs", "status", "units_count"]
        
        values_list = []
        for f in fields:
            if f == "property_id":
                values_list.append(property_id)
            elif f == "status":
                values_list.append(data.get(f, "Active"))
            elif f == "units_count":
                values_list.append(data.get(f, 0))
            else:
                values_list.append(data.get(f))
                
        placeholders = ", ".join(["%s"] * len(fields))
        columns = ", ".join(fields)
        
        sql = f"INSERT INTO properties ({columns}) VALUES ({placeholders}) RETURNING property_id;"
        
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, values_list)
                result = await cur.fetchone()
                await conn.commit()
                return result[0] if result else property_id

    async def update_property(self, property_id: str, data: Dict[str, Any]) -> bool:
        """
        Updates an existing property record.
        """
        if not data:
            return True

        db_url = self._url()
        updates = []
        params = []
        
        allowed_fields = ["title", "address", "city", "property_type", "price_lakhs", "status", "units_count"]
        
        for k, v in data.items():
            if k in allowed_fields and v is not None:
                updates.append(f"{k} = %s")
                params.append(v)
                
        if not updates:
            return True
            
        params.append(property_id)
        
        sql = f"UPDATE properties SET {', '.join(updates)} WHERE property_id = %s;"
        
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                await conn.commit()
                return cur.rowcount > 0

    async def delete_property(self, property_id: str) -> bool:
        """
        Deletes a property record from PostgreSQL.
        Disassociates or removes child records across all dependent tables:
          - conversations, tenants, maintenance_tickets, human_escalations, renewal_reminders, renewal_intents (property_id = NULL)
          - lease_expiry_events, leases, units (deleted)
        """
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                # 1. Disassociate tables where property_id is nullable
                dependent_tables = [
                    "conversations",
                    "tenants",
                    "maintenance_tickets",
                    "human_escalations",
                    "renewal_reminders",
                    "renewal_intents",
                ]
                for table in dependent_tables:
                    try:
                        await cur.execute(
                            f"UPDATE {table} SET property_id = NULL WHERE property_id = %s;",
                            (property_id,)
                        )
                    except Exception as e:
                        logger.warning(f"Could not update {table} property_id: {e}")

                # 2. Clean up child records tied directly to property
                for table in ["lease_expiry_events", "leases", "units"]:
                    try:
                        await cur.execute(
                            f"DELETE FROM {table} WHERE property_id = %s;",
                            (property_id,)
                        )
                    except Exception as e:
                        logger.warning(f"Could not delete from {table}: {e}")

                # 3. Delete the property itself
                await cur.execute(
                    "DELETE FROM properties WHERE property_id = %s;",
                    (property_id,)
                )
                await conn.commit()
                return cur.rowcount > 0

    async def toggle_property_status(self, property_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """
        Toggles a property between Active and Inactive status.
        """
        if new_status not in ("Active", "Inactive"):
            new_status = "Active"
            
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "UPDATE properties SET status = %s WHERE property_id = %s RETURNING property_id;",
                    (new_status, property_id)
                )
                result = await cur.fetchone()
                await conn.commit()
                if not result:
                    return None
                return await self.get_property_by_id(property_id)

    async def get_property_dashboard_cards(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        property_type: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Returns property cards with REAL computed conversation stats from PostgreSQL.
        Each card includes: conversations_count, maintenance_count, escalations_count,
        and active_automations — all queried from live database tables.
        """
        db_url = self._url()
        conditions = []
        params: List[Any] = []

        if search:
            conditions.append("(LOWER(p.title) LIKE LOWER(%s) OR LOWER(p.city) LIKE LOWER(%s) OR LOWER(p.address) LIKE LOWER(%s))")
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
        if status:
            conditions.append("LOWER(p.status) = LOWER(%s)")
            params.append(status)
        if property_type:
            conditions.append("LOWER(p.property_type) = LOWER(%s)")
            params.append(property_type)
        if city:
            conditions.append("LOWER(p.city) = LOWER(%s)")
            params.append(city)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        sql = f"""
            SELECT
                p.property_id,
                p.title,
                p.address,
                p.city,
                p.property_type,
                p.price_lakhs,
                COALESCE(p.status, 'Active') AS status,
                COALESCE(p.units_count, 0) AS units_count,
                p.created_at,
                -- Real conversation stats from PostgreSQL conversations table
                COALESCE(conv_stats.conversations_count, 0) AS conversations_count,
                COALESCE(conv_stats.maintenance_count, 0) AS maintenance_count,
                COALESCE(conv_stats.escalations_count, 0) AS escalations_count
            FROM properties p
            LEFT JOIN (
                SELECT
                    property_id,
                    COUNT(*)::int AS conversations_count,
                    COUNT(*) FILTER (WHERE intent = 'Maintenance Request')::int AS maintenance_count,
                    COUNT(*) FILTER (WHERE status = 'Escalated')::int AS escalations_count
                FROM conversations
                GROUP BY property_id
            ) conv_stats ON conv_stats.property_id = p.property_id
            {where_clause}
            ORDER BY p.created_at DESC
            LIMIT %s;
        """

        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()

                cards = []
                for r in rows:
                    card = dict(r)
                    # Fetch active automations linked to this property
                    card["active_automations"] = await self._get_property_automations(
                        cur, r["property_id"]
                    )
                    cards.append(card)

                return cards

    async def _get_property_automations(
        self, cur, property_id: str
    ) -> List[str]:
        """
        Returns list of active automation names relevant to this property.
        Checks if the automation scope includes 'All Properties' or this specific property.
        """
        try:
            await cur.execute(
                """
                SELECT name FROM automations
                WHERE status = 'Active'
                AND (
                    scope LIKE '%%All Properties%%'
                    OR scope LIKE %s
                )
                ORDER BY name ASC
                LIMIT 5;
                """,
                (f"%{property_id}%",)
            )
            rows = await cur.fetchall()
            return [r["name"] for r in rows]
        except Exception:
            # If automations table doesn't exist yet, return empty
            return []

    async def get_distinct_cities(self) -> List[str]:
        """Returns distinct city values from properties for filter dropdowns."""
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT DISTINCT city FROM properties WHERE city IS NOT NULL ORDER BY city ASC;")
                rows = await cur.fetchall()
                return [r["city"] for r in rows]


# Shared singleton instance
property_repository = PropertyRepository()
