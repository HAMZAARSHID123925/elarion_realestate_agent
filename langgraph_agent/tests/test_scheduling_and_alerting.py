"""
Phase 5 Test Suite — Scheduling, Job Locking, Retries, Dead-Letter, Maintenance SLA & Alerts.
"""
import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure paths are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from fastapi.testclient import TestClient

from app.server import app
from app.jobs.locks import JobLockManager, JobAlreadyRunningError, job_name_to_lock_id
from app.jobs.alerts import alert_service
from app.jobs.runner import JobRunner
from app.jobs.maintenance_monitor import check_stale_maintenance_tickets
from app.jobs.registry import JOB_REGISTRY
from app.jobs.scheduler import platform_scheduler
from database.dead_letter_repository import DeadLetterRepository, sanitize_payload

client = TestClient(app)


# ── Job Locking Tests (PostgreSQL Advisory & Fallback) ────────────────────────

@pytest.mark.asyncio
async def test_job_lock_acquisition_and_release_local():
    lock_mgr = JobLockManager(db_url=None)
    assert not lock_mgr.is_locked("test_job")

    async with lock_mgr.acquire("test_job"):
        assert lock_mgr.is_locked("test_job")

    assert not lock_mgr.is_locked("test_job")


@pytest.mark.asyncio
async def test_job_lock_concurrency_rejection():
    lock_mgr = JobLockManager(db_url=None)

    async with lock_mgr.acquire("exclusive_job"):
        # Second attempt while locked must raise JobAlreadyRunningError
        with pytest.raises(JobAlreadyRunningError):
            async with lock_mgr.acquire("exclusive_job"):
                pass


@pytest.mark.asyncio
async def test_job_lock_postgresql_advisory_lock_success():
    lock_mgr = JobLockManager(db_url="postgresql://test:test@localhost:5432/test")
    lock_id = job_name_to_lock_id("rent_reminder_scan")
    assert isinstance(lock_id, int)

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = (True,)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__aexit__.return_value = None
    mock_conn.close = AsyncMock()

    with patch("psycopg.AsyncConnection.connect", new_callable=AsyncMock, return_value=mock_conn):
        async with lock_mgr.acquire("rent_reminder_scan"):
            assert lock_mgr.is_locked("rent_reminder_scan")
            # Verify advisory lock was queried
            mock_cursor.execute.assert_any_call("SELECT pg_try_advisory_lock(%s);", (lock_id,))

        # Verify advisory unlock was called
        mock_cursor.execute.assert_any_call("SELECT pg_advisory_unlock(%s);", (lock_id,))
        mock_conn.close.assert_awaited()


@pytest.mark.asyncio
async def test_job_lock_postgresql_advisory_lock_already_held():
    lock_mgr = JobLockManager(db_url="postgresql://test:test@localhost:5432/test")

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = (False,)  # Lock held by another worker

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__aexit__.return_value = None
    mock_conn.close = AsyncMock()

    with patch("psycopg.AsyncConnection.connect", new_callable=AsyncMock, return_value=mock_conn):
        with pytest.raises(JobAlreadyRunningError):
            async with lock_mgr.acquire("concurrent_job"):
                pass


# ── Alert Service Tests ───────────────────────────────────────────────────────

def test_alert_service_rent_escalation():
    alert_service.clear_history()
    alert = alert_service.send_rent_escalation_alert(
        tenant_id="T-100",
        tenant_name="Fatima Ali",
        property_address="Flat 2A, Clifton, Karachi",
        rent_amount=95000.0,
        days_overdue=36,
        reason="No response to Reminder 1 or Follow-up 2"
    )
    assert alert["alert_type"] == "RENT_ARREARS_ESCALATION"
    assert alert["severity"] == "HIGH"
    assert alert["metadata"]["tenant_id"] == "T-100"
    assert alert["metadata"]["days_overdue"] == 36

    recent = alert_service.get_recent_alerts(limit=10)
    assert len(recent) == 1
    assert recent[0]["alert_id"] == alert["alert_id"]


def test_alert_service_maintenance_emergency():
    alert_service.clear_history()
    alert = alert_service.send_maintenance_emergency_alert(
        ticket_id="TICK-999",
        category="plumbing",
        description="Active sewage backup in main bathroom",
        urgency="high",
        unassigned_hours=2.5
    )
    assert alert["alert_type"] == "MAINTENANCE_EMERGENCY_SLA_BREACH"
    assert alert["severity"] == "CRITICAL"
    assert alert["metadata"]["ticket_id"] == "TICK-999"


# ── Job Runner & Retry / Dead-Letter Tests ─────────────────────────────────────

@pytest.mark.asyncio
async def test_job_runner_success():
    runner = JobRunner()

    async def sample_task():
        return {"records": 10, "status": "ok"}

    telemetry = await runner.execute_job("sample_job", sample_task)
    assert telemetry["status"] == "SUCCESS"
    assert telemetry["attempts"] == 1
    assert telemetry["duration_ms"] >= 0.0
    assert telemetry["result_summary"]["records"] == 10


@pytest.mark.asyncio
async def test_job_runner_retry_success():
    runner = JobRunner()
    attempts_made = 0

    async def flaky_task():
        nonlocal attempts_made
        attempts_made += 1
        if attempts_made == 1:
            raise ConnectionError("Temporary DB blip")
        return {"recovered": True}

    telemetry = await runner.execute_job("flaky_job", flaky_task, max_retries=2, initial_backoff=0.01)
    assert telemetry["status"] == "SUCCESS"
    assert telemetry["attempts"] == 2
    assert telemetry["result_summary"]["recovered"] is True


@pytest.mark.asyncio
async def test_job_runner_dead_letter_on_exhaustion():
    runner = JobRunner()
    alert_service.clear_history()

    async def failing_task():
        raise RuntimeError("Permanent database corruption")

    telemetry = await runner.execute_job("fatal_job", failing_task, max_retries=2, initial_backoff=0.01)
    assert telemetry["status"] == "DEAD_LETTER"
    assert telemetry["attempts"] == 3
    assert "Permanent database corruption" in telemetry["error_message"]

    # Verify dead-letter records
    dlq = await runner.get_dead_letter_records()
    assert len(dlq) >= 1
    assert any(r["job_name"] == "fatal_job" for r in dlq)

    # Verify alert was emitted
    alerts = alert_service.get_recent_alerts()
    assert any(a["alert_type"] == "JOB_DEAD_LETTER_FAILURE" for a in alerts)


def test_dead_letter_payload_sanitization():
    raw_payload = {
        "user": "test_user",
        "password": "SuperSecretPassword123!",
        "api_key": "sk-1234567890abcdef",
        "data": {"token": "jwt-token-val", "number": 42}
    }
    sanitized = sanitize_payload(raw_payload)
    assert "SuperSecretPassword123!" not in sanitized
    assert "sk-1234567890abcdef" not in sanitized
    assert "jwt-token-val" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized
    assert "test_user" in sanitized


@pytest.mark.asyncio
async def test_dead_letter_repository_persistence():
    repo = DeadLetterRepository(db_url=None)  # In-memory mode
    rec = await repo.create_dead_letter_record(
        job_name="test_expiry",
        attempts=3,
        error_type="TimeoutError",
        error_message="Gateway timeout",
        duration_ms=150.0,
        payload={"secret_key": "hidden", "lease_id": "L-101"}
    )
    assert rec["dead_letter_id"].startswith("DLQ-")
    assert rec["job_name"] == "test_expiry"
    assert "[REDACTED_SECRET]" in rec["payload_summary"]

    records = await repo.list_dead_letter_records()
    assert len(records) == 1
    assert records[0]["dead_letter_id"] == rec["dead_letter_id"]


# ── Maintenance SLA Monitor & Deduplication Tests ─────────────────────────────

@pytest.mark.asyncio
async def test_maintenance_sla_monitor_and_deduplication():
    now = datetime.now(timezone.utc)
    mock_tickets = [
        # Emergency ticket unassigned for 2 hours (not yet escalated) -> ALERT & RECORD
        {
            "ticket_id": "TICK-EMERGENCY-1",
            "category": "electrical",
            "description": "Sparking fuse box",
            "urgency": "high",
            "assignment_status": "UNASSIGNED",
            "escalation_level": None,
            "created_at": (now - timedelta(hours=2)).isoformat()
        },
        # Emergency ticket unassigned for 3 hours (ALREADY ESCALATED) -> SUPPRESS DUPLICATE
        {
            "ticket_id": "TICK-EMERGENCY-ALREADY-ESCALATED",
            "category": "plumbing",
            "description": "Flooding basement",
            "urgency": "high",
            "assignment_status": "UNASSIGNED",
            "escalation_level": "EMERGENCY_SLA",
            "last_escalated_at": (now - timedelta(hours=1)).isoformat(),
            "created_at": (now - timedelta(hours=3)).isoformat()
        },
        # Standard ticket unassigned for 30 hours -> ALERT & RECORD
        {
            "ticket_id": "TICK-STANDARD-1",
            "category": "general",
            "description": "Loose door handle",
            "urgency": "low",
            "assignment_status": "UNASSIGNED",
            "escalation_level": None,
            "created_at": (now - timedelta(hours=30)).isoformat()
        }
    ]

    with patch("app.jobs.maintenance_monitor.maintenance_repository.list_tickets", new_callable=AsyncMock, return_value=mock_tickets), \
         patch("app.jobs.maintenance_monitor.maintenance_repository.record_ticket_escalation", new_callable=AsyncMock) as mock_record:

        summary = await check_stale_maintenance_tickets()
        assert summary["status"] == "completed"
        assert summary["scanned"] == 3
        assert summary["emergency_alerts"] == 1  # Only 1 emergency alert (the second was deduplicated)
        assert summary["stale_alerts"] == 1      # 1 standard alert
        assert summary["deduplicated_skips"] == 1 # 1 duplicate skipped
        assert mock_record.call_count == 2       # Recorded 2 new escalations


# ── Scheduler & Registry Tests ────────────────────────────────────────────────

def test_job_registry_contains_core_jobs():
    assert "rent_reminder_scan" in JOB_REGISTRY
    assert "lease_expiry_scan" in JOB_REGISTRY
    assert "renewal_reminder_scan" in JOB_REGISTRY
    assert "maintenance_sla_monitor" in JOB_REGISTRY


@pytest.mark.asyncio
async def test_platform_scheduler_lifecycle():
    assert not platform_scheduler.is_running()
    await platform_scheduler.start()
    assert platform_scheduler.is_running()
    await platform_scheduler.stop()
    assert not platform_scheduler.is_running()


# ── Jobs REST API Tests ───────────────────────────────────────────────────────

def test_api_list_jobs():
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    names = [j["job_name"] for j in data]
    assert "rent_reminder_scan" in names
    assert "lease_expiry_scan" in names
    assert "renewal_reminder_scan" in names
    assert "maintenance_sla_monitor" in names


def test_api_trigger_job_success():
    with patch("app.api.routers.jobs.run_registered_job", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {
            "job_name": "rent_reminder_scan",
            "status": "SUCCESS",
            "attempts": 1,
            "duration_ms": 125.4,
            "result_summary": {"records_scanned": 5, "reminders_sent": 2}
        }
        response = client.post("/api/v1/jobs/rent_reminder_scan/run")
        assert response.status_code == 200
        data = response.json()
        assert data["job_name"] == "rent_reminder_scan"
        assert data["status"] == "SUCCESS"
        assert data["attempts"] == 1


def test_api_trigger_job_not_found():
    response = client.post("/api/v1/jobs/nonexistent_job/run")
    assert response.status_code == 404
    data = response.json()
    assert "not registered" in data["message"]


def test_api_list_dead_letter_and_alerts():
    response_dlq = client.get("/api/v1/jobs/dead-letter")
    assert response_dlq.status_code == 200
    assert isinstance(response_dlq.json(), list)

    response_alerts = client.get("/api/v1/jobs/alerts")
    assert response_alerts.status_code == 200
    assert isinstance(response_alerts.json(), list)
