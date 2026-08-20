"""
Dashboard Repository — Phase 7 API Layer.

Provides data aggregation for the dashboard overview.
"""
import os
import logging
from typing import Dict, Any, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url

class DashboardRepository:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> str:
        return self._db_url or get_db_url()

    async def get_overview_metrics(self) -> Dict[str, Any]:
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                metrics = {}
                
                # Total properties
                await cur.execute("SELECT COUNT(*) as count FROM properties;")
                row = await cur.fetchone()
                metrics["total_properties"] = row["count"] if row else 0
                
                # Total tenants
                await cur.execute("SELECT COUNT(*) as count FROM tenants;")
                row = await cur.fetchone()
                metrics["total_tenants"] = row["count"] if row else 0
                
                # Active leases
                await cur.execute("SELECT COUNT(*) as count FROM leases WHERE status = 'active';")
                row = await cur.fetchone()
                metrics["active_leases"] = row["count"] if row else 0
                
                # Open maintenance tickets
                await cur.execute("SELECT COUNT(*) as count FROM maintenance_tickets WHERE status = 'OPEN';")
                row = await cur.fetchone()
                metrics["open_maintenance_tickets"] = row["count"] if row else 0
                
                # Open escalations
                await cur.execute("SELECT COUNT(*) as count FROM human_escalations WHERE status != 'RESOLVED' AND status != 'CLOSED';")
                row = await cur.fetchone()
                metrics["open_escalations"] = row["count"] if row else 0
                
                # Outstanding rent
                await cur.execute("SELECT COALESCE(SUM(rent_amount), 0) as total FROM tenants WHERE payment_status != 'paid';")
                row = await cur.fetchone()
                metrics["outstanding_rent"] = float(row["total"]) if row else 0.0

                return metrics

dashboard_repository = DashboardRepository()
