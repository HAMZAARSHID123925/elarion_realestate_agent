"""
API Layer Test Suite — Phase 4 Verification.

Tests all endpoints across Health, Tenants, Properties, Maintenance, Workflows, FAQ, and Pipeline.
Validates 200 success, 201 creation, 404 not found, 422 validation errors, and standardized error envelopes.
"""
import sys
import os
from unittest.mock import patch, AsyncMock

# Ensure langgraph_agent and root are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from fastapi.testclient import TestClient

from app.server import app

client = TestClient(app)


# ── Health & Readiness Tests ──────────────────────────────────────────────────

def test_health_check_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "elarion-core-api"
    assert "timestamp" in data


def test_readiness_check_success():
    with patch("database.tenant_repository.tenant_repository.check_connection", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"


def test_readiness_check_failure():
    with patch("database.tenant_repository.tenant_repository.check_connection", side_effect=Exception("Connection refused")):
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "disconnected" in data["database"]


# ── Tenants API Tests ─────────────────────────────────────────────────────────

def test_list_tenants_success():
    mock_tenants = [
        {
            "tenant_id": "T-001",
            "name": "Ahmed Khan",
            "property_address": "Apt 4B, Gulberg Heights",
            "rent_due_date": "2026-07-01",
            "rent_amount": 75000.0,
            "payment_status": "overdue",
            "manual_hold": False,
            "last_reminder_status": "day_30_sent"
        }
    ]
    with patch("database.tenant_repository.tenant_repository.get_unpaid_overdue_tenants", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_tenants
        response = client.get("/api/v1/tenants?overdue_only=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["tenant_id"] == "T-001"
        assert data[0]["rent_amount"] == 75000.0


def test_get_tenant_by_id_success():
    mock_tenant = {
        "tenant_id": "T-001",
        "tenant_name": "Ahmed Khan",
        "property_address": "Apt 4B, Gulberg Heights",
        "rent_due_date": "2026-07-01",
        "rent_amount": 75000.0,
        "payment_status": "overdue",
        "manual_hold": False,
        "last_reminder_status": "day_30_sent",
        "reminder_30_sent_at": "2026-08-01T08:00:00",
        "response_received": False,
        "human_escalated": False
    }
    with patch("database.tenant_repository.tenant_repository.get_tenant_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_tenant
        response = client.get("/api/v1/tenants/T-001")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "T-001"
        assert data["tenant_name"] == "Ahmed Khan"


def test_get_tenant_by_id_not_found():
    with patch("database.tenant_repository.tenant_repository.get_tenant_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get("/api/v1/tenants/T-NONEXISTENT")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "not found" in data["message"]


def test_set_manual_hold_success():
    mock_tenant = {"tenant_id": "T-001", "name": "Ahmed Khan"}
    with patch("database.tenant_repository.tenant_repository.get_tenant_by_id", new_callable=AsyncMock) as mock_get, \
         patch("database.tenant_repository.tenant_repository.set_manual_hold", new_callable=AsyncMock) as mock_set:
        mock_get.return_value = mock_tenant
        response = client.post("/api/v1/tenants/T-001/hold", json={"manual_hold": True})
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "T-001"
        assert data["manual_hold"] is True
        assert "enabled" in data["message"]
        mock_set.assert_called_once_with("T-001", True)


def test_set_manual_hold_validation_error():
    response = client.post("/api/v1/tenants/T-001/hold", json={"manual_hold": "not_a_boolean"})
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"


# ── Properties API Tests ──────────────────────────────────────────────────────

def test_list_properties_success():
    mock_props = [
        {
            "property_id": "PROP-001",
            "title": "Gulberg Luxury Heights",
            "address": "Gulberg III, Lahore",
            "city": "Lahore",
            "property_type": "apartment",
            "price_lakhs": 250.0,
            "created_at": None
        }
    ]
    with patch("database.property_repository.property_repository.list_properties", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_props
        response = client.get("/api/v1/properties?city=Lahore")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["property_id"] == "PROP-001"
        assert data[0]["city"] == "Lahore"


def test_get_property_by_id_success():
    mock_prop = {
        "property_id": "PROP-001",
        "title": "Gulberg Luxury Heights",
        "address": "Gulberg III, Lahore",
        "city": "Lahore",
        "property_type": "apartment",
        "price_lakhs": 250.0,
        "created_at": None
    }
    mock_units = [
        {"unit_id": "U-101", "property_id": "PROP-001", "unit_number": "101", "created_at": None},
        {"unit_id": "U-102", "property_id": "PROP-001", "unit_number": "102", "created_at": None}
    ]
    with patch("database.property_repository.property_repository.get_property_by_id", new_callable=AsyncMock) as mock_get, \
         patch("database.property_repository.property_repository.get_property_units", new_callable=AsyncMock) as mock_units_get:
        mock_get.return_value = mock_prop
        mock_units_get.return_value = mock_units

        response = client.get("/api/v1/properties/PROP-001")
        assert response.status_code == 200
        data = response.json()
        assert data["property_id"] == "PROP-001"
        assert len(data["units"]) == 2


def test_get_property_by_id_not_found():
    with patch("database.property_repository.property_repository.get_property_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get("/api/v1/properties/PROP-999")
        assert response.status_code == 404


# ── Maintenance Tickets API Tests ─────────────────────────────────────────────

def test_list_maintenance_tickets_success():
    mock_tickets = [
        {
            "ticket_id": "TICK-001",
            "tenant_id": "T-001",
            "property_id": "PROP-001",
            "unit_id": "U-101",
            "category": "plumbing",
            "description": "Pipe leaking under kitchen sink",
            "urgency": "medium",
            "status": "OPEN",
            "vendor_id": "VEND-001",
            "assignment_status": "ASSIGNED",
            "created_at": None
        }
    ]
    with patch("database.maintenance_repository.maintenance_repository.list_tickets", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_tickets
        response = client.get("/api/v1/maintenance/tickets?status=OPEN")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["ticket_id"] == "TICK-001"


def test_create_maintenance_ticket_success():
    mock_created = {
        "ticket_id": "TICK-NEW1",
        "tenant_id": "T-001",
        "property_id": "PROP-001",
        "unit_id": "U-101",
        "category": "electrical",
        "description": "Main circuit breaker keeps tripping",
        "urgency": "high",
        "status": "OPEN",
        "vendor_id": None,
        "assignment_status": "UNASSIGNED",
        "created_at": None
    }
    with patch("database.maintenance_repository.maintenance_repository.create_ticket", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_created
        payload = {
            "tenant_id": "T-001",
            "property_id": "PROP-001",
            "unit_id": "U-101",
            "category": "electrical",
            "description": "Main circuit breaker keeps tripping",
            "urgency": "high"
        }
        response = client.post("/api/v1/maintenance/tickets", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["ticket_id"] == "TICK-NEW1"
        assert data["category"] == "electrical"


def test_create_maintenance_ticket_validation_error():
    # Missing description and category
    response = client.post("/api/v1/maintenance/tickets", json={"tenant_id": "T-001"})
    assert response.status_code == 422


def test_get_maintenance_ticket_by_id_success():
    mock_ticket = {
        "ticket_id": "TICK-001",
        "tenant_id": "T-001",
        "category": "plumbing",
        "description": "Pipe leaking",
        "urgency": "medium",
        "status": "OPEN",
        "vendor_id": "VEND-001",
        "assignment_status": "ASSIGNED",
        "created_at": None
    }
    mock_logs = [
        {"log_id": 1, "ticket_id": "TICK-001", "old_status": None, "new_status": "OPEN", "timestamp": None}
    ]
    with patch("database.maintenance_repository.maintenance_repository.get_ticket_by_id", new_callable=AsyncMock) as mock_get, \
         patch("database.maintenance_repository.maintenance_repository.get_ticket_status_log", new_callable=AsyncMock) as mock_logs_get:
        mock_get.return_value = mock_ticket
        mock_logs_get.return_value = mock_logs

        response = client.get("/api/v1/maintenance/tickets/TICK-001")
        assert response.status_code == 200
        data = response.json()
        assert data["ticket_id"] == "TICK-001"
        assert len(data["status_history"]) == 1


# ── Workflow Triggers API Tests ───────────────────────────────────────────────

def test_trigger_rent_reminder_batch():
    mock_summary = {
        "records_scanned": 5,
        "reminders_sent": 2,
        "followups_sent": 1,
        "escalated": 1,
        "skipped": 1
    }
    with patch("app.api.routers.workflows.run_daily_rent_reminder_workflow", return_value=mock_summary):
        response = client.post("/api/v1/workflows/rent-reminder/run")
        assert response.status_code == 200
        data = response.json()
        assert data["records_scanned"] == 5
        assert data["reminders_sent"] == 2
        assert data["escalated"] == 1


def test_evaluate_single_tenant_workflow():
    mock_final_state = {
        "tenant_id": "T-001",
        "action": "SEND_REMINDER_1",
        "last_reminder_status": "day_30_sent",
        "days_overdue": 30,
        "rent_amount": 75000.0,
        "logs": ["[TEST] Reminder 1 dispatched"]
    }
    with patch("app.api.routers.workflows.rent_reminder_graph.invoke", return_value=mock_final_state):
        response = client.post("/api/v1/workflows/rent-reminder/evaluate", json={"tenant_id": "T-001"})
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "T-001"
        assert data["action"] == "SEND_REMINDER_1"
        assert data["days_overdue"] == 30


def test_trigger_lease_expiry_scan():
    mock_summary = {
        "leases_scanned": 12,
        "events_created": 3,
        "run_id": "run-test-123"
    }
    with patch("app.api.routers.workflows.run_lease_expiry_scan", new_callable=AsyncMock, return_value=mock_summary):
        response = client.post("/api/v1/workflows/lease-expiry/scan")
        assert response.status_code == 200
        data = response.json()
        assert data["scanned"] == 12
        assert data["events_created"] == 3
        assert data["run_id"] == "run-test-123"


def test_trigger_renewal_reminder_scan():
    mock_summary = {
        "pending_events_scanned": 8,
        "reminders_sent": 4,
        "run_id": "run-test-456"
    }
    with patch("app.api.routers.workflows.run_renewal_reminder_dispatch", new_callable=AsyncMock, return_value=mock_summary):
        response = client.post("/api/v1/workflows/renewal-reminder/scan")
        assert response.status_code == 200
        data = response.json()
        assert data["scanned"] == 8
        assert data["reminders_sent"] == 4


# ── FAQ & Master Pipeline API Tests ───────────────────────────────────────────

def test_faq_query_endpoint():
    mock_state = {
        "final_response": "Office hours are Monday through Friday from 9 AM to 6 PM."
    }
    with patch("app.api.routers.faq.faq_graph.ainvoke", new_callable=AsyncMock, return_value=mock_state):
        response = client.post("/api/v1/faq/query", json={"query": "What are the office hours?"})
        assert response.status_code == 200
        data = response.json()
        assert "Office hours" in data["answer"]


def test_pipeline_message_endpoint():
    mock_result = {
        "final_response": "I have created maintenance ticket TICK-123 for your AC issue.",
        "intent": "maintenance",
        "active_department": "maintenance"
    }
    with patch("app.api.routers.pipeline.invoke_pipeline", new_callable=AsyncMock, return_value=(mock_result, {})):
        payload = {
            "channel": "api",
            "user_id": "+923001234567",
            "text": "My AC is making a loud noise and blowing warm air."
        }
        response = client.post("/api/v1/pipeline/message", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "maintenance"
        assert "TICK-123" in data["final_response"]
