"""
Automation Repository — Core Dashboard & Database Data Layer.

Provides data access methods for workflow automations, PostgreSQL persistence,
dynamic configuration updates, and audit logging.
Uses shared connection pool from database.pool.
"""
import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from psycopg.rows import dict_row
from dotenv import load_dotenv

from database.audit_repository import audit_repository
from database.pool import get_db_connection, get_database_url

# Ensure root directory environment variables are loaded
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for env_path in [os.path.join(root_dir, ".env"), os.path.join(root_dir, "langgraph_agent", ".env")]:
    if os.path.exists(env_path):
        load_dotenv(env_path)

load_dotenv()
logger = logging.getLogger(__name__)


def get_db_url() -> str:
    return get_database_url()


# Default seed data fallback in case database connection fails or is uninitialized
DEFAULT_AUTOMATIONS: List[Dict[str, Any]] = [
    {
        "id": "maintenance_request",
        "name": "Maintenance Request",
        "status": "Active",
        "description": "Handles: Collect details, classify urgency, ticket creation, vendor assignment.",
        "tagline": "End-to-end ticket triage, vendor dispatch, and tenant notification.",
        "handles": ["Collect details", "classify urgency", "ticket creation", "vendor assignment"],
        "channels": ["WhatsApp", "Email", "Voice", "Web"],
        "escalation_conditions": [
            "Emergency detected (e.g., flood)",
            "AI confidence < 85%",
            "Estimate > $500 requires sign-off",
            "Primary vendor unavailable"
        ],
        "scope": "All Properties (42)",
        "properties_count": 42,
        "icon_type": "maintenance"
    },
    {
        "id": "rent_reminder",
        "name": "Rent Reminder",
        "status": "Active",
        "description": "Handles: Payment status check, day 30/35 notices, direct WhatsApp reminder.",
        "tagline": "Automated ledger tracking with polite multi-channel escalation.",
        "handles": ["Payment status check", "day 30/35 notices", "direct WhatsApp reminder"],
        "channels": ["WhatsApp", "SMS", "Email"],
        "escalation_conditions": [
            "Payment overdue > 5 days after reminder",
            "Tenant disputes charge amount",
            "Payment plan requested",
            "Manual hold requested by PM"
        ],
        "scope": "All Properties (42)",
        "properties_count": 42,
        "icon_type": "rent"
    },
    {
        "id": "resident_support",
        "name": "Resident Support",
        "status": "Active",
        "description": "Handles: Building rules, parking policies, amenities booking, package queries.",
        "tagline": "24/7 instant AI Q&A backed by building policy vector search.",
        "handles": ["Building rules", "parking policies", "amenities booking", "package queries"],
        "channels": ["WhatsApp", "Web", "Email"],
        "escalation_conditions": [
            "Policy conflict or ambiguous rule",
            "Noise complaint against neighbor",
            "Tenant requests property manager callback",
            "Sentiment negative / agitated tone"
        ],
        "scope": "All Properties (42)",
        "properties_count": 42,
        "icon_type": "support"
    },
    {
        "id": "lease_renewal",
        "name": "Leasing / Renewal",
        "status": "Active",
        "description": "Handles: Expiry detection (90/60/30d), intent classification, offer generation.",
        "tagline": "Proactive tenant retention pipeline with dynamic rent calculation.",
        "handles": ["Expiry detection (90/60/30d)", "intent classification", "offer generation"],
        "channels": ["Email", "WhatsApp"],
        "escalation_conditions": [
            "Tenant proposes counter-offer on rate",
            "Tenant requests lease term exception",
            "Intent to vacate confirmed",
            "Renewal deadline < 14 days with no response"
        ],
        "scope": "All Properties (42)",
        "properties_count": 42,
        "icon_type": "lease"
    },
    {
        "id": "owner_reporting",
        "name": "Owner Reporting",
        "status": "Inactive",
        "description": "Handles: Monthly statement compilation, occupancy metrics, maintenance cost breakdown.",
        "tagline": "Automated monthly financial rollup & investor distribution.",
        "handles": ["Monthly statement compilation", "occupancy metrics", "maintenance cost breakdown"],
        "channels": ["Email", "Web Portal"],
        "escalation_conditions": [
            "Revenue drop > 10% vs prior month",
            "Capital expenditure > $2,000",
            "Owner requests custom report format",
            "Audit log discrepancy detected"
        ],
        "scope": "Selected Properties (18)",
        "properties_count": 18,
        "icon_type": "reporting"
    }
]


class AutomationRepository:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> Optional[str]:
        return self._db_url

    def _format_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures JSON-encoded columns are returned as native Python lists."""
        d = dict(row)
        for key in ["handles", "channels", "escalation_conditions", "steps"]:
            val = d.get(key)
            if isinstance(val, str):
                try:
                    d[key] = json.loads(val)
                except Exception:
                    d[key] = [s.strip() for s in val.split(",") if s.strip()]
            elif val is None:
                d[key] = []
        return d

    async def list_automations(self) -> List[Dict[str, Any]]:
        """
        Returns all automation records from PostgreSQL, falling back to seed defaults if DB is empty.
        """
        try:
            async with get_db_connection(self._url()) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("SELECT * FROM automations ORDER BY created_at ASC;")
                    rows = await cur.fetchall()
                    if rows:
                        return [self._format_row(r) for r in rows]
        except Exception as e:
            logger.warning(f"Could not read automations from PostgreSQL ({e}). Using static fallback.")

        return DEFAULT_AUTOMATIONS

    async def get_automation_by_id(self, automation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single automation by ID from PostgreSQL.
        """
        try:
            async with get_db_connection(self._url()) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("SELECT * FROM automations WHERE id = %s;", (automation_id,))
                    row = await cur.fetchone()
                    if row:
                        return self._format_row(row)
        except Exception as e:
            logger.warning(f"Could not fetch automation #{automation_id} from PostgreSQL ({e}).")

        # Check default seed list fallback
        for item in DEFAULT_AUTOMATIONS:
            if item["id"] == automation_id:
                return item
        return None

    async def update_automation(
        self,
        automation_id: str,
        updates: Dict[str, Any],
        actor: str = "property_manager"
    ) -> Optional[Dict[str, Any]]:
        """
        Updates an existing automation record in PostgreSQL, creates an audit log entry,
        and returns the updated object.
        """
        before_state = await self.get_automation_by_id(automation_id)

        # Handle 'active' boolean input mapping to 'status' string ('Active' | 'Inactive')
        if "active" in updates and updates["active"] is not None:
            updates["status"] = "Active" if updates["active"] else "Inactive"
            del updates["active"]

        fields = []
        params = []

        allowed_keys = ["name", "status", "description", "tagline", "handles", "channels", "escalation_conditions", "steps", "scope", "properties_count", "icon_type"]

        for key in allowed_keys:
            if key in updates and updates[key] is not None:
                val = updates[key]
                if key in ["handles", "channels", "escalation_conditions", "steps"] and isinstance(val, (list, dict)):
                    val = json.dumps(val)
                fields.append(f"{key} = %s")
                params.append(val)

        if not fields:
            return before_state

        fields.append("updated_at = NOW()")
        params.append(automation_id)

        set_clause = ", ".join(fields)
        query = f"UPDATE automations SET {set_clause} WHERE id = %s RETURNING *;"

        after_state = None

        try:
            async with get_db_connection(self._url()) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, params)
                    row = await cur.fetchone()
                    if hasattr(conn, "commit") and not getattr(conn, "autocommit", False):
                        await conn.commit()
                    if row:
                        after_state = self._format_row(row)
        except Exception as e:
            logger.error(f"Error updating automation #{automation_id} in PostgreSQL: {e}")
            if before_state:
                after_state = dict(before_state)
                for k, v in updates.items():
                    if k in allowed_keys and v is not None:
                        after_state[k] = v

        if after_state:
            try:
                asyncio.create_task(audit_repository.create_audit_log(
                    action="UPDATE_AUTOMATION",
                    actor=actor,
                    details=f"Updated automation rules for '{automation_id}'",
                    before_state=before_state,
                    after_state=after_state
                ))
            except Exception as audit_err:
                logger.warning(f"Audit log entry for automation update failed: {audit_err}")

        return after_state

    async def create_automation(
        self,
        data: Dict[str, Any],
        actor: str = "property_manager"
    ) -> Dict[str, Any]:
        """
        Inserts a new custom automation configuration into PostgreSQL.
        """
        name = data.get("name", "Custom Workflow Automation")
        raw_id = data.get("id") or name.lower().replace(" ", "_").replace("/", "_")
        auto_id = "".join(c for c in raw_id if c.isalnum() or c == "_")

        status = data.get("status", "Active")
        description = data.get("description", f"Custom workflow automation for {name}.")
        tagline = data.get("tagline", "Custom property management workflow.")
        handles = json.dumps(data.get("handles", [name]))
        channels = json.dumps(data.get("channels", ["Email", "WhatsApp"]))
        escalation_conditions = json.dumps(data.get("escalation_conditions", ["Manual review requested"]))
        scope = data.get("scope", "All Properties (42)")
        properties_count = data.get("properties_count", 42)
        icon_type = data.get("icon_type", "maintenance")

        query = """
            INSERT INTO automations (id, name, status, description, tagline, handles, channels, escalation_conditions, scope, properties_count, icon_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                status = EXCLUDED.status,
                description = EXCLUDED.description,
                tagline = EXCLUDED.tagline,
                handles = EXCLUDED.handles,
                channels = EXCLUDED.channels,
                escalation_conditions = EXCLUDED.escalation_conditions,
                scope = EXCLUDED.scope,
                updated_at = NOW()
            RETURNING *;
        """

        res = None
        try:
            async with get_db_connection(self._url()) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, (auto_id, name, status, description, tagline, handles, channels, escalation_conditions, scope, properties_count, icon_type))
                    row = await cur.fetchone()
                    if hasattr(conn, "commit") and not getattr(conn, "autocommit", False):
                        await conn.commit()
                    if row:
                        res = self._format_row(row)
        except Exception as e:
            logger.error(f"Error creating automation '{name}' in PostgreSQL: {e}")

        if not res:
            res = {
                "id": auto_id,
                "name": name,
                "status": status,
                "description": description,
                "tagline": tagline,
                "handles": data.get("handles", [name]),
                "channels": data.get("channels", ["Email", "WhatsApp"]),
                "escalation_conditions": data.get("escalation_conditions", ["Manual review requested"]),
                "scope": scope,
                "properties_count": properties_count,
                "icon_type": icon_type
            }

        try:
            asyncio.create_task(audit_repository.create_audit_log(
                action="CREATE_AUTOMATION",
                actor=actor,
                details=f"Created new automation '{name}' (#{auto_id})",
                after_state=res
            ))
        except Exception as audit_err:
            logger.warning(f"Audit log entry for automation creation failed: {audit_err}")

        return res

    async def delete_automation(
        self,
        automation_id: str,
        actor: str = "property_manager"
    ) -> bool:
        """
        Deletes an automation record from PostgreSQL and logs a DELETE_AUTOMATION audit entry.
        """
        before_state = await self.get_automation_by_id(automation_id)

        try:
            async with get_db_connection(self._url()) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("DELETE FROM automations WHERE id = %s;", (automation_id,))
                    if hasattr(conn, "commit") and not getattr(conn, "autocommit", False):
                        await conn.commit()
        except Exception as e:
            logger.error(f"Error deleting automation #{automation_id} from PostgreSQL: {e}")

        try:
            asyncio.create_task(audit_repository.create_audit_log(
                action="DELETE_AUTOMATION",
                actor=actor,
                details=f"Deleted automation '{before_state.get('name', automation_id) if before_state else automation_id}' (#{automation_id})",
                before_state=before_state
            ))
        except Exception as audit_err:
            logger.warning(f"Audit log entry for automation deletion failed: {audit_err}")

        return True


# Shared singleton repository
automation_repository = AutomationRepository()
