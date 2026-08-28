"""
Comprehensive Test Suite for Rent Reminder & Human Escalation Workflows — Phase 3 Live Data Wired.
Tests state transitions, pure decision logic, database updates, batch execution,
TenantRepository, live data hydration, joining date relative cycles, missing-tenant handling, and dynamic responses.
"""
import pytest
import os
import sys
import asyncio
from datetime import date

# Ensure root directories are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from database.rent_models import seed_sample_tenants, get_tenant_by_id, get_db_path
from database.tenant_repository import TenantRepository, tenant_repository
from app.core_workflows.rent_reminder.nodes import reminder_decision_node, payment_check_node
from app.core_workflows.rent_reminder.graph import rent_reminder_graph
from app.core_workflows.rent_reminder.scheduler import run_daily_rent_reminder_workflow, AutomatedRentScheduler
from app.department_nodes import run_rent_reminder
from app.orchestrator.schemas import UnifiedRequest
from app.pipeline_state import PipelineState

TEST_DB = os.path.join(os.path.dirname(__file__), "test_rent.db")


@pytest.fixture(autouse=True)
def setup_test_db():
    """Sets up a clean test database with 5 sample tenants before each test."""
    os.environ["DB_PATH"] = TEST_DB
    seed_sample_tenants(db_path=TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_decision_node_unit_tests():
    """Tests all pure rule decisions in reminder_decision_node."""
    # Test Ali Ahmed (Joined 1st): Day 30 Billing Cycle Reminder #1
    state_1 = {
        "tenant_id": "T-101",
        "joining_date": "2026-07-01",
        "rent_due_date": "2026-07-31",
        "days_overdue": 5,
        "reminder_30_sent_at": None,
        "payment_status": "overdue",
        "manual_hold": False,
        "current_date": "2026-08-05",
        "logs": []
    }
    result_1 = reminder_decision_node(state_1)
    assert result_1["action"] == "SEND_REMINDER"

    # Test Furqan Khan (Joined 11th): Days 31-35 Unpaid Warning Notice #2
    state_2 = {
        "tenant_id": "T-102",
        "joining_date": "2026-07-11",
        "rent_due_date": "2026-08-10",
        "days_overdue": 0,
        "reminder_30_sent_at": "2026-08-01",
        "reminder_5_sent_at": None,
        "payment_status": "reminder_sent",
        "manual_hold": False,
        "current_date": "2026-08-05",
        "logs": []
    }
    result_2 = reminder_decision_node(state_2)
    assert result_2["action"] == "SEND_FOLLOWUP"

    # Test Day 36+ Direct Human Escalation
    state_3 = {
        "tenant_id": "T-103",
        "joining_date": "2026-06-20",
        "rent_due_date": "2026-07-20",
        "days_overdue": 16,
        "reminder_30_sent_at": "2026-07-20",
        "reminder_5_sent_at": "2026-07-26",
        "human_escalated": False,
        "response_received": False,
        "payment_status": "followup_sent",
        "manual_hold": False,
        "current_date": "2026-08-05",
        "logs": []
    }
    result_3 = reminder_decision_node(state_3)
    assert result_3["action"] == "ESCALATE"

    # Test Manual Hold Skip
    state_4 = {
        "tenant_id": "T-104",
        "joining_date": "2026-06-15",
        "rent_due_date": "2026-07-15",
        "days_overdue": 20,
        "manual_hold": True,
        "payment_status": "overdue",
        "current_date": "2026-08-05",
        "logs": []
    }
    result_4 = reminder_decision_node(state_4)
    assert result_4["action"] == "SKIP"


def test_payment_check_node_live_hydration():
    """Validates that payment_check_node hydrates tenant data when only tenant_id is provided."""
    sparse_state = {
        "tenant_id": "T-101",
        "current_date": "2026-08-05",
        "logs": []
    }
    result = payment_check_node(sparse_state)

    # Verify hydrated fields
    assert result["tenant_name"] == "Ali Ahmed"
    assert result["property_address"] == "Flat 4B, Gulberg Heights, Lahore"
    assert result["rent_amount"] == 75000.0
    assert result["rent_due_date"] == "2026-07-31"
    assert result["days_overdue"] == 5
    assert "error" not in result or result["error"] is None


def test_payment_check_node_missing_tenant_handled():
    """Validates controlled handling when a tenant_id does not exist in the database."""
    missing_state = {
        "tenant_id": "NON_EXISTENT_TENANT",
        "current_date": "2026-08-05",
        "logs": []
    }
    result = payment_check_node(missing_state)

    assert result["action"] == "SKIP"
    assert result["error"] == "tenant_not_found"
    assert result["days_overdue"] == 0
    assert any("Tenant NON_EXISTENT_TENANT not found" in log for log in result["logs"])

    # Verify decision node preserves skip decision
    decision = reminder_decision_node(result)
    assert decision["action"] == "SKIP"


def test_graph_execution_with_hydrated_tenant():
    """Tests complete graph execution when starting from only tenant_id."""
    initial_input = {
        "tenant_id": "T-101",
        "current_date": "2026-08-05",
        "logs": []
    }
    graph_result = rent_reminder_graph.invoke(initial_input)

    assert graph_result["action"] == "SEND_REMINDER"
    assert graph_result["last_reminder_status"] == "reminder_sent"
    assert graph_result["rent_amount"] == 75000.0

    # Verify database persistence
    t101 = get_tenant_by_id("T-101", db_path=TEST_DB)
    assert t101["last_reminder_status"] == "reminder_sent"
    assert t101["reminder_30_sent_at"] == "2026-08-05"


@pytest.mark.asyncio
async def test_run_rent_reminder_dynamic_response():
    """Validates that run_rent_reminder returns dynamic data-driven responses."""
    # 1. Existing Overdue Tenant (T-101)
    req = UnifiedRequest(
        channel="whatsapp",
        user_id="T-101",
        raw_text="When is my rent due?",
        channel_metadata={}
    )
    pipeline_state: PipelineState = {
        "request": req,
        "active_department": None,
        "department_result": None,
        "final_response": None,
    }
    res = await run_rent_reminder(pipeline_state, config={})
    assert res["active_department"] is None
    assert "Ali Ahmed" in res["final_response"]
    assert "75,000.00" in res["final_response"]

    # 2. Missing Tenant
    req_missing = UnifiedRequest(
        channel="whatsapp",
        user_id="T-9999",
        raw_text="Check my rent",
        channel_metadata={}
    )
    pipeline_state_missing: PipelineState = {
        "request": req_missing,
        "active_department": None,
        "department_result": None,
        "final_response": None,
    }
    res_missing = await run_rent_reminder(pipeline_state_missing, config={})
    assert "could not find a tenant record" in res_missing["final_response"]


def test_daily_scheduler_batch_execution():
    """Runs full daily workflow scan and checks summary counts & DB state updates."""
    summary = run_daily_rent_reminder_workflow(current_date_str="2026-08-05")

    # Verify summary stats
    assert summary["records_scanned"] == 4  # T-105 is paid, so excluded from overdue query
    assert summary["reminders_sent"] == 1   # T-101 (Ali Ahmed)
    assert summary["followups_sent"] == 1   # T-102 (Furqan Khan - Days 31-35 Warning)
    assert summary["escalated"] == 1        # T-103 (Day 36 Direct Human Escalation)
    assert summary["skipped"] == 1          # T-104 (Manual hold)

    # Verify DB persistence for T-101 (Ali Ahmed: Reminder #1 sent)
    t101 = get_tenant_by_id("T-101", db_path=TEST_DB)
    assert t101["reminder_30_sent_at"] == "2026-08-05"
    assert t101["last_reminder_status"] == "reminder_sent"

    # Verify DB persistence for T-102 (Furqan Khan: Warning Notice #2 sent)
    t102 = get_tenant_by_id("T-102", db_path=TEST_DB)
    assert t102["reminder_5_sent_at"] == "2026-08-05"
    assert t102["last_reminder_status"] == "followup_sent"

    # Verify DB persistence for T-103 (Day 36 Direct Human Escalation)
    t103 = get_tenant_by_id("T-103", db_path=TEST_DB)
    assert t103["human_escalated"] == 1
    assert t103["last_reminder_status"] == "escalated"
    assert "Day 36 Threshold Reached" in t103["escalation_reason"]

def test_automated_rent_scheduler_service():
    """Tests starting and stopping the AutomatedRentScheduler background task."""
    async def run_test():
        scheduler = AutomatedRentScheduler(interval_seconds=1)
        scheduler.start()
        assert scheduler._running is True
        await asyncio.sleep(0.1)
        await scheduler.stop()
        assert scheduler._running is False

    asyncio.run(run_test())


def test_tenant_repository_initialization():
    """Validates TenantRepository construction and configuration."""
    repo = TenantRepository(db_url="postgresql://user:pass@localhost:5432/testdb")
    assert repo._url() == "postgresql://user:pass@localhost:5432/testdb"
    assert tenant_repository is not None


if __name__ == "__main__":
    pytest.main(["-v", __file__])

