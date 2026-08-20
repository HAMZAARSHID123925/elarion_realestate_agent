"""
Conversation Repository — Core Dashboard Data Layer.

Provides data access methods for conversations, chat message transcripts,
filtering, pagination, and real-time status updates.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

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


class ConversationRepository:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> str:
        return self._db_url or get_db_url()

    async def list_conversations(
        self,
        search: Optional[str] = None,
        property_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        channel: Optional[str] = None,
        intent: Optional[str] = None,
        urgency: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Fetches paginated conversations with optional filters."""
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                where_clauses = []
                params = []

                if search:
                    where_clauses.append("(c.contact_name ILIKE %s OR c.conversation_id ILIKE %s OR p.title ILIKE %s)")
                    pattern = f"%{search}%"
                    params.extend([pattern, pattern, pattern])

                if property_id and property_id.lower() != "all properties":
                    where_clauses.append("c.property_id = %s")
                    params.append(property_id)

                if unit_id:
                    where_clauses.append("c.unit_id ILIKE %s")
                    params.append(f"%{unit_id}%")

                if channel and channel.lower() != "all channels":
                    where_clauses.append("c.channel ILIKE %s")
                    params.append(channel)

                if intent and intent.lower() != "all intents":
                    where_clauses.append("c.intent ILIKE %s")
                    params.append(intent)

                if urgency and urgency.lower() != "all levels":
                    where_clauses.append("c.urgency ILIKE %s")
                    params.append(urgency)

                if status and status.lower() != "all statuses":
                    where_clauses.append("c.status ILIKE %s")
                    params.append(status)

                where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

                # Count query
                count_query = f"""
                    SELECT COUNT(*) as total 
                    FROM conversations c
                    LEFT JOIN properties p ON c.property_id = p.property_id
                    {where_sql}
                """
                await cur.execute(count_query, params)
                count_row = await cur.fetchone()
                total_count = count_row["total"] if count_row else 0

                # Data query
                data_query = f"""
                    SELECT 
                        c.conversation_id,
                        c.tenant_id,
                        c.property_id,
                        COALESCE(p.title, c.property_id, 'Sunset Apartments') as property_name,
                        c.unit_id,
                        COALESCE(u.unit_number, c.unit_id, 'Unit 204') as unit_number,
                        c.contact_name,
                        c.channel,
                        c.intent,
                        c.urgency,
                        c.status,
                        c.workflow_triggered,
                        c.human_intervention,
                        c.is_reviewed,
                        c.last_message_at,
                        c.created_at
                    FROM conversations c
                    LEFT JOIN properties p ON c.property_id = p.property_id
                    LEFT JOIN units u ON c.unit_id = u.unit_id
                    {where_sql}
                    ORDER BY c.last_message_at DESC
                    LIMIT %s OFFSET %s
                """
                await cur.execute(data_query, params + [limit, offset])
                rows = await cur.fetchall()

                return {
                    "total": total_count,
                    "items": [dict(r) for r in rows],
                    "limit": limit,
                    "offset": offset
                }

    async def get_conversation_detail(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Returns metadata and transcript messages for a specific conversation."""
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                # Fetch conversation header
                await cur.execute("""
                    SELECT 
                        c.conversation_id,
                        c.tenant_id,
                        c.property_id,
                        COALESCE(p.title, 'Sunset Apartments') as property_name,
                        c.unit_id,
                        COALESCE(u.unit_number, '204') as unit_number,
                        c.contact_name,
                        c.channel,
                        c.intent,
                        c.urgency,
                        c.status,
                        c.workflow_triggered,
                        c.human_intervention,
                        c.is_reviewed,
                        c.last_message_at,
                        c.created_at
                    FROM conversations c
                    LEFT JOIN properties p ON c.property_id = p.property_id
                    LEFT JOIN units u ON c.unit_id = u.unit_id
                    WHERE c.conversation_id = %s
                """, [conversation_id])
                conv = await cur.fetchone()
                if not conv:
                    return None

                # Fetch messages
                await cur.execute("""
                    SELECT 
                        message_id,
                        sender_type,
                        sender_name,
                        content,
                        system_event,
                        timestamp
                    FROM conversation_messages
                    WHERE conversation_id = %s
                    ORDER BY timestamp ASC
                """, [conversation_id])
                messages = await cur.fetchall()

                return conv_dict

    async def record_turn_and_update_state(
        self,
        conversation_id: str,
        contact_name: str,
        channel: str,
        tenant_text: str,
        ai_response: str,
        intent: Optional[str] = None,
        active_department: Optional[str] = None
    ) -> None:

        """Production Atomic State Machine — records turns, updates conversation status & creates human escalation tickets."""
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                # 1. Evaluate State Machine Flags
                low_text = (tenant_text + " " + ai_response).lower()
                is_emergency = any(kw in low_text for kw in ["fire", "flood", "leak", "gas smell", "emergency", "smoke", "carbon monoxide"])
                is_escalated = is_emergency or any(kw in low_text for kw in [
                    "connect you with a team member", 
                    "submitted your request for review", 
                    "human required", 
                    "escalat",
                    "trouble understanding"
                ])

                status_val = "Escalated" if is_escalated else "AI Resolved"
                urgency_val = "CRITICAL" if is_emergency else "Normal"
                intervention_val = "Property Manager" if is_escalated else "None"
                workflow_val = active_department or "Resident Support"

                # 2. Upsert Conversation Header (Atomic)
                await cur.execute("""
                    INSERT INTO conversations (
                        conversation_id, contact_name, channel, intent, urgency, status, workflow_triggered, human_intervention, last_message_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (conversation_id) DO UPDATE SET 
                        contact_name = EXCLUDED.contact_name,
                        status = EXCLUDED.status,
                        urgency = EXCLUDED.urgency,
                        workflow_triggered = EXCLUDED.workflow_triggered,
                        human_intervention = EXCLUDED.human_intervention,
                        last_message_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """, [conversation_id, contact_name, channel, intent or "General Inquiry", urgency_val, status_val, workflow_val, intervention_val])

                # 3. Append Tenant Message
                await cur.execute("""
                    INSERT INTO conversation_messages (conversation_id, sender_type, sender_name, content)
                    VALUES (%s, 'tenant', %s, %s)
                """, [conversation_id, contact_name, tenant_text])

                # 4. Append AI Message
                await cur.execute("""
                    INSERT INTO conversation_messages (conversation_id, sender_type, sender_name, content)
                    VALUES (%s, 'ai', 'TenantFlow AI', %s)
                """, [conversation_id, ai_response])

                # 5. Insert Escalation Record if Escalated (Atomic)
                if is_escalated:
                    escalation_reason = "Emergency Triage" if is_emergency else "AI Handover Request"
                    severity = "CRITICAL" if is_emergency else "ESCALATION"
                    desc = f"{contact_name}: {tenant_text[:120]}"

                    await cur.execute("""
                        INSERT INTO human_escalations (
                            lease_id, tenant_id, property_id, escalation_reason, escalation_priority, status, description, assigned_to
                        ) VALUES (
                            (SELECT lease_id FROM leases LIMIT 1),
                            (SELECT tenant_id FROM tenants LIMIT 1),
                            (SELECT property_id FROM properties LIMIT 1),
                            %s, %s, 'OPEN', %s, 'Property Manager'
                        )
                    """, [escalation_reason, severity, desc])


                await conn.commit()

    async def mark_reviewed(self, conversation_id: str) -> bool:
        """Marks a conversation as reviewed by property manager."""
        db_url = self._url()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("""
                    UPDATE conversations SET is_reviewed = TRUE, updated_at = CURRENT_TIMESTAMP WHERE conversation_id = %s
                """, [conversation_id])
                await conn.commit()
                return cur.rowcount > 0


conversation_repository = ConversationRepository()

