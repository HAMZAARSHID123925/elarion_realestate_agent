"""
Comprehensive Test Suite for Phase 2 — Renewal Reminder (Workflow #4).

Tests:
  - Template Engine: 90, 60, 30, 7 days, and expired window templates.
  - Channel Dispatcher: Email, WhatsApp, and Mock fallback.
  - Service Batch Orchestrator: Batch processing of PENDING expiry events,
    idempotent reminder history tracking, and error isolation.
  - LangGraph Nodes & Subgraph: Decision routing, state transitions, and audit logging.
"""
import pytest
import os
import sys
from datetime import date, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure root directories are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


# ============================================================================
# 1. Template Engine Unit Tests
# ============================================================================

from app.core_workflows.rent_renewal.renewal_reminder.templates import (
    get_template_subject_and_body,
    render_renewal_reminder_message,
)


class TestRenewalReminderTemplates:
    """Tests for renewal reminder message templates."""

    def test_90_day_template(self):
        subject, body = get_template_subject_and_body(
            window_days=90,
            tenant_name="Hamza Arshid",
            property_address="Apt 4B, Gulberg Heights",
            expiry_date_str="2026-11-10",
            monthly_rent=75000.0,
            days_remaining=90,
        )
        assert "90 Days" in subject
        assert "Hamza Arshid" in body
        assert "Apt 4B, Gulberg Heights" in body
        assert "2026-11-10" in body
        assert "75,000.00" in body
        assert "90 days" in body

    def test_60_day_template(self):
        subject, body = get_template_subject_and_body(
            window_days=60,
            tenant_name="Zainab Bibi",
            property_address="Villa 12, DHA Phase 5",
            expiry_date_str="2026-10-10",
            monthly_rent=120000.0,
            days_remaining=60,
        )
        assert "60 Days" in subject
        assert "Zainab Bibi" in body
        assert "120,000.00" in body
        assert "60 days" in body

    def test_30_day_template(self):
        subject, body = get_template_subject_and_body(
            window_days=30,
            tenant_name="John Doe",
            property_address="House 88, Bahria Town",
            expiry_date_str="2026-09-10",
            monthly_rent=95000.0,
            days_remaining=30,
        )
        assert "IMPORTANT" in subject
        assert "30 Days" in subject
        assert "John Doe" in body
        assert "30 days" in body

    def test_7_day_template(self):
        subject, body = get_template_subject_and_body(
            window_days=7,
            tenant_name="Ali Malik",
            property_address="Studio 15, Clifton",
            expiry_date_str="2026-08-17",
            monthly_rent=50000.0,
            days_remaining=7,
        )
        assert "URGENT" in subject
        assert "7 Days" in subject
        assert "FINAL NOTICE" in body
        assert "Ali Malik" in body

    def test_expired_template(self):
        subject, body = get_template_subject_and_body(
            window_days=0,
            tenant_name="Usman Tariq",
            property_address="House 12, F-10 Islamabad",
            expiry_date_str="2026-08-05",
            monthly_rent=110000.0,
            days_remaining=-5,
        )
        assert "Expired" in subject
        assert "Usman Tariq" in body
        assert "expired on 2026-08-05" in body


# ============================================================================
# 2. Channel Dispatcher Unit Tests
# ============================================================================

from app.core_workflows.rent_renewal.renewal_reminder.channels import dispatch_reminder


class TestChannelDispatcher:
    """Tests for multi-channel dispatch."""

    @pytest.mark.asyncio
    async def test_mock_email_dispatch_when_unconfigured(self):
        """When RESEND_API_KEY is not configured, dispatches gracefully via mock."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("RESEND_API_KEY", None)
            res = await dispatch_reminder(
                recipient="tenant@example.com",
                subject="Lease Renewal Notice",
                body="Test body",
                channel="email",
            )
            assert res["success"] is True
            assert res["status"] == "MOCKED"
            assert res["channel"] == "email"

    @pytest.mark.asyncio
    async def test_mock_whatsapp_dispatch_when_unconfigured(self):
        """When WhatsApp token is not configured, dispatches gracefully via mock."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("WHATSAPP_ACCESS_TOKEN", None)
            res = await dispatch_reminder(
                recipient="+923001234567",
                subject="Renewal Notice",
                body="Test body",
                channel="whatsapp",
            )
            assert res["success"] is True
            assert res["status"] == "MOCKED"
            assert res["channel"] == "whatsapp"


# ============================================================================
# 3. Service Batch Dispatch Integration Tests (mocked repository)
# ============================================================================

from app.core_workflows.rent_renewal.renewal_reminder.service import run_renewal_reminder_dispatch


class TestRenewalReminderService:
    """Tests for the Phase 2 batch orchestrator."""

    @pytest.fixture(autouse=True)
    def mock_repo_and_channels(self):
        with patch(
            "app.core_workflows.rent_renewal.renewal_reminder.service.repository"
        ) as mock_repo, patch(
            "app.core_workflows.rent_renewal.renewal_reminder.service.dispatch_reminder",
            new_callable=AsyncMock,
        ) as mock_dispatch:
            mock_repo.get_pending_expiry_events = AsyncMock(return_value=[])
            mock_repo.record_renewal_reminder = AsyncMock(return_value=101)
            mock_repo.mark_expiry_event_status = AsyncMock()
            mock_dispatch.return_value = {
                "success": True,
                "status": "SENT",
                "message_id": "msg-12345",
            }
            self.mock_repo = mock_repo
            self.mock_dispatch = mock_dispatch
            yield

    @pytest.mark.asyncio
    async def test_empty_batch(self):
        """When no pending expiry events exist, summary shows zero processed."""
        self.mock_repo.get_pending_expiry_events.return_value = []
        summary = await run_renewal_reminder_dispatch()

        assert summary["status"] == "COMPLETED"
        assert summary["events_scanned"] == 0
        assert summary["reminders_sent"] == 0

    @pytest.mark.asyncio
    async def test_batch_processes_pending_events(self):
        """Processes pending events, renders templates, and updates event statuses to SENT."""
        self.mock_repo.get_pending_expiry_events.return_value = [
            {
                "event_id": 1,
                "event_name": "LEASE_EXPIRY_90_DAYS",
                "lease_id": "L-001",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "expiry_date": date(2026, 11, 10),
                "days_remaining": 90,
                "window_days": 90,
                "event_date": date(2026, 8, 10),
                "event_status": "PENDING",
                "run_id": "scan-123",
                "tenant_name": "Hamza Arshid",
                "tenant_contact": "hamza@example.com",
                "property_address": "123 Main St Apt 4B",
                "monthly_rent": 75000.0,
                "lease_status": "active",
            },
            {
                "event_id": 2,
                "event_name": "LEASE_EXPIRY_30_DAYS",
                "lease_id": "L-002",
                "tenant_id": "T-101",
                "property_id": "P-100",
                "expiry_date": date(2026, 9, 10),
                "days_remaining": 30,
                "window_days": 30,
                "event_date": date(2026, 8, 10),
                "event_status": "PENDING",
                "run_id": "scan-123",
                "tenant_name": "John Doe",
                "tenant_contact": "+923001112222",
                "property_address": "123 Main St Unit 12",
                "monthly_rent": 95000.0,
                "lease_status": "active",
            },
        ]

        summary = await run_renewal_reminder_dispatch()

        assert summary["status"] == "COMPLETED"
        assert summary["events_scanned"] == 2
        assert summary["reminders_sent"] == 2
        assert self.mock_dispatch.call_count == 2
        assert self.mock_repo.record_renewal_reminder.call_count == 2
        assert self.mock_repo.mark_expiry_event_status.call_count == 2
        self.mock_repo.mark_expiry_event_status.assert_any_call(1, "SENT")
        self.mock_repo.mark_expiry_event_status.assert_any_call(2, "SENT")

    @pytest.mark.asyncio
    async def test_per_event_error_isolation(self):
        """Failure on one event does not abort processing of other events."""
        self.mock_repo.get_pending_expiry_events.return_value = [
            {
                "event_id": 1,
                "event_name": "LEASE_EXPIRY_90_DAYS",
                "lease_id": "L-001",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "expiry_date": date(2026, 11, 10),
                "days_remaining": 90,
                "window_days": 90,
                "tenant_name": "Hamza Arshid",
                "tenant_contact": "hamza@example.com",
                "property_address": "123 Main St",
                "monthly_rent": 75000.0,
            },
            {
                "event_id": 2,
                "event_name": "LEASE_EXPIRY_60_DAYS",
                "lease_id": "L-002",
                "tenant_id": "T-101",
                "property_id": "P-100",
                "expiry_date": date(2026, 10, 10),
                "days_remaining": 60,
                "window_days": 60,
                "tenant_name": "John Doe",
                "tenant_contact": "john@example.com",
                "property_address": "123 Main St",
                "monthly_rent": 95000.0,
            },
        ]

        # Make first dispatch fail, second succeed
        self.mock_dispatch.side_effect = [
            {"success": False, "status": "FAILED", "error": "SMTP Timeout"},
            {"success": True, "status": "SENT", "message_id": "msg-2"},
        ]

        summary = await run_renewal_reminder_dispatch()

        assert summary["events_scanned"] == 2
        assert summary["reminders_sent"] == 1
        assert summary["reminders_failed"] == 1
        self.mock_repo.mark_expiry_event_status.assert_any_call(1, "FAILED")
        self.mock_repo.mark_expiry_event_status.assert_any_call(2, "SENT")


# ============================================================================
# 4. LangGraph Subgraph & Nodes Tests
# ============================================================================

from app.core_workflows.rent_renewal.nodes import (
    lease_check_node,
    renewal_reminder_decision_node,
    renewal_reminder_send_node,
    renewal_reminder_tracker_node,
)
from app.core_workflows.rent_renewal.graph import rent_renewal_graph


class TestRentRenewalNodes:
    """Tests for LangGraph nodes and decision logic."""

    def test_lease_check_node_calculation(self):
        """Calculates days_to_expiry and assigns correct stage."""
        today = date.today()
        state = {
            "tenant_id": "T-100",
            "lease_end_date": (today + timedelta(days=60)).isoformat(),
            "logs": [],
        }
        res = lease_check_node(state)
        assert res["days_to_expiry"] == 60
        assert res["expiry_stage"] == "60_DAYS"
        assert res["renewal_status"] == "APPROACHING_EXPIRY"

    def test_reminder_decision_node_send_action(self):
        """When reminder hasn't been sent yet, decides SEND_REMINDER."""
        state = {
            "expiry_stage": "60_DAYS",
            "last_reminder_type": None,
            "logs": [],
        }
        res = renewal_reminder_decision_node(state)
        assert res["action"] == "SEND_REMINDER"

    def test_reminder_decision_node_skip_duplicate(self):
        """When reminder for this stage was already sent, decides SKIP."""
        state = {
            "expiry_stage": "60_DAYS",
            "last_reminder_type": "LEASE_EXPIRY_60_DAYS",
            "logs": [],
        }
        res = renewal_reminder_decision_node(state)
        assert res["action"] == "SKIP"

    def test_reminder_decision_node_skip_future(self):
        """When lease is far in the future, decides SKIP."""
        state = {
            "expiry_stage": "FUTURE",
            "logs": [],
        }
        res = renewal_reminder_decision_node(state)
        assert res["action"] == "SKIP"

    @pytest.mark.asyncio
    async def test_end_to_end_subgraph_execution(self):
        """Executes full LangGraph rent_renewal subgraph."""
        today = date.today()
        initial_state = {
            "tenant_id": "T-100",
            "tenant_name": "Hamza Arshid",
            "tenant_contact": "hamza@example.com",
            "property_address": "123 Main St Apt 4B",
            "lease_end_date": (today + timedelta(days=30)).isoformat(),
            "monthly_rent": 75000.0,
            "reminder_count": 0,
            "logs": [],
        }

        with patch(
            "app.core_workflows.rent_renewal.nodes.reminder_send_node.dispatch_reminder",
            new_callable=AsyncMock,
        ) as mock_disp:
            mock_disp.return_value = {"success": True, "status": "SENT"}
            result = await rent_renewal_graph.ainvoke(initial_state)

        assert result["is_complete"] is True
        assert result["renewal_status"] == "REMINDER_SENT"
        assert result["reminder_count"] == 1
        assert result["last_reminder_type"] == "LEASE_EXPIRY_30_DAYS"
        assert "30 days" in result["last_reminder_body"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
