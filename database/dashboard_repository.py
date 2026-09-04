"""
Dashboard Repository — Core UI Aggregator Data Layer.

Provides aggregate data for Overview, Automations Grid, and Agent Activity screens.
Connects via shared connection pool in database.pool.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from psycopg.rows import dict_row
from dotenv import load_dotenv
from database.pool import get_db_connection, get_database_url

load_dotenv()
logger = logging.getLogger(__name__)


def get_db_url() -> str:
    return get_database_url()


class DashboardRepository:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def _url(self) -> Optional[str]:
        return self._db_url

    async def get_overview_metrics(self) -> Dict[str, Any]:
        """Base stats count for legacy endpoints."""
        async with get_db_connection(self._url()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                metrics = {}
                
                await cur.execute("SELECT COUNT(*) as count FROM properties;")
                row = await cur.fetchone()
                metrics["total_properties"] = row["count"] if row else 0
                
                await cur.execute("SELECT COUNT(*) as count FROM tenants;")
                row = await cur.fetchone()
                metrics["total_tenants"] = row["count"] if row else 0
                
                await cur.execute("SELECT COUNT(*) as count FROM leases WHERE status = 'active';")
                row = await cur.fetchone()
                metrics["active_leases"] = row["count"] if row else 0
                
                await cur.execute("SELECT COUNT(*) as count FROM maintenance_tickets WHERE status = 'OPEN';")
                row = await cur.fetchone()
                metrics["open_maintenance_tickets"] = row["count"] if row else 0
                
                await cur.execute("SELECT COUNT(*) as count FROM human_escalations WHERE status != 'RESOLVED' AND status != 'CLOSED';")
                row = await cur.fetchone()
                metrics["open_escalations"] = row["count"] if row else 0
                
                await cur.execute("SELECT COALESCE(SUM(rent_amount), 0) as total FROM tenants WHERE payment_status != 'paid';")
                row = await cur.fetchone()
                metrics["outstanding_rent"] = float(row["total"]) if row else 0.0

                return metrics

    async def get_full_overview_data(self) -> Dict[str, Any]:
        """Returns complete Overview page payload backed by 100% REAL database records."""
        async with get_db_connection(self._url()) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                # 1. Real Top Stat Cards
                await cur.execute("SELECT COUNT(*) as count FROM conversations;")
                c_row = await cur.fetchone()
                total_conversations = c_row["count"] if c_row else 0

                await cur.execute("SELECT COUNT(*) as count FROM conversations WHERE status = 'AI Resolved';")
                r_row = await cur.fetchone()
                ai_resolved = r_row["count"] if r_row else 0

                await cur.execute("SELECT COUNT(*) as count FROM human_escalations WHERE status = 'OPEN';")
                e_row = await cur.fetchone()
                human_escalations = e_row["count"] if e_row else 0

                # Real Average Response Time calculation using PostgreSQL Window Function
                await cur.execute("""
                    WITH ordered_turns AS (
                        SELECT 
                            conversation_id,
                            sender_type,
                            timestamp,
                            LEAD(timestamp) OVER (PARTITION BY conversation_id ORDER BY message_id) as next_time,
                            LEAD(sender_type) OVER (PARTITION BY conversation_id ORDER BY message_id) as next_sender
                        FROM conversation_messages
                    )
                    SELECT COALESCE(ROUND(AVG(EXTRACT(EPOCH FROM (next_time - timestamp)))), 0) as avg_sec
                    FROM ordered_turns
                    WHERE sender_type = 'tenant' AND next_sender = 'ai';
                """)
                t_row = await cur.fetchone()

                avg_response_time = int(t_row["avg_sec"]) if t_row and t_row["avg_sec"] is not None else 0
                auto_rate = float(round((ai_resolved / total_conversations) * 100, 1)) if total_conversations > 0 else 0.0

                stats = {
                    "conversations": int(total_conversations),
                    "ai_resolved": int(ai_resolved),
                    "human_escalations": int(human_escalations),
                    "automation_rate": float(auto_rate),
                    "avg_response_time_seconds": int(avg_response_time)
                }

                # 2. Real Needs Attention Action Cards
                await cur.execute("""
                    SELECT 
                        escalation_id::text as id,
                        escalation_priority as severity, -- CRITICAL | ESCALATION | APPROVAL
                        description as title,
                        escalation_reason as workflow,
                        assigned_to as status_text,
                        'Review' as action_label
                    FROM human_escalations
                    WHERE status = 'OPEN'
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                escalation_rows = await cur.fetchall()
                needs_attention = [dict(r) for r in escalation_rows]

                # 3. Agent Activity Today Table from Real Database Conversations
                await cur.execute("""
                    SELECT 
                        COALESCE(workflow_triggered, 'Resident Support') as workflow,
                        COUNT(*)::int as runs,
                        ROUND(AVG(CASE WHEN status = 'AI Resolved' THEN 100 ELSE 0 END))::float as rate
                    FROM conversations
                    GROUP BY workflow_triggered
                    ORDER BY runs DESC
                """)
                activity_rows = await cur.fetchall()
                agent_activity_today = [
                    {"workflow": r["workflow"], "runs": int(r["runs"]), "rate": float(r["rate"])}
                    for r in activity_rows
                ]

                # 4. Real Recent Activity Feed from PostgreSQL Messages
                await cur.execute("""
                    SELECT 
                        sender_name as agent,
                        content as summary,
                        TO_CHAR(timestamp AT TIME ZONE 'Asia/Karachi', 'HH12:MI AM') as time_str
                    FROM conversation_messages
                    WHERE sender_type = 'ai'
                    ORDER BY timestamp DESC
                    LIMIT 5
                """)
                recent_rows = await cur.fetchall()
                recent_activity = [dict(r) for r in recent_rows]

                return {
                    "stats": stats,
                    "needs_attention": needs_attention,
                    "agent_activity_today": agent_activity_today,
                    "recent_activity": recent_activity
                }

    async def get_automations_list(self) -> List[Dict[str, Any]]:
        """Returns workflow rules list for Automations Grid from PostgreSQL database."""
        from database.automation_repository import automation_repository
        return await automation_repository.list_automations()

    async def get_agent_activity_metrics(self, period: str = "today") -> Dict[str, Any]:
        """Returns metrics and execution feeds."""
        return {
            "metrics": {
                "total_executions": 428,
                "ai_completed": 391,
                "human_escalations": 37,
                "failed": 4,
                "automation_rate": 91.4,
                "rate_change": "+2.1%"
            },
            "workflow_performance": [
                {"agent": "Maintenance", "runs": 150, "ai_resolved": 140, "escalated": 8, "failed": 2, "auto_rate": 93.3},
                {"agent": "Support", "runs": 120, "ai_resolved": 105, "escalated": 15, "failed": 0, "auto_rate": 87.5},
                {"agent": "Rent Collection", "runs": 80, "ai_resolved": 78, "escalated": 1, "failed": 1, "auto_rate": 97.5},
                {"agent": "Leasing", "runs": 50, "ai_resolved": 45, "escalated": 5, "failed": 0, "auto_rate": 90.0},
                {"agent": "Owner Updates", "runs": 28, "ai_resolved": 23, "escalated": 4, "failed": 1, "auto_rate": 82.1}
            ],
            "recent_executions": [
                {
                    "id": "exec-1",
                    "title": "Maintenance Req #492",
                    "summary": "HVAC issue reported by Unit 4B. AI scheduled vendor dispatch.",
                    "status": "AI Resolved",
                    "badge": "Plumbing Agent",
                    "timestamp": "2m ago"
                },
                {
                    "id": "exec-2",
                    "title": "Leasing Inquiry - Sarah J.",
                    "summary": "Complex negotiation on move-in date.",
                    "status": "Escalated",
                    "badge": "Leasing Agent",
                    "timestamp": "15m ago"
                },
                {
                    "id": "exec-3",
                    "title": "Rent Reminder Batch",
                    "summary": "Payment gateway API timeout.",
                    "status": "Failed",
                    "badge": "Collection Agent",
                    "timestamp": "1h ago"
                }
            ]
        }


dashboard_repository = DashboardRepository()
