"""
Phase 6 Test Suite — Security, RBAC, Middleware, Audit Logging, Metrics & Hardening.
"""
import sys
import os
import io
import json
import logging
from unittest.mock import patch, AsyncMock

# Ensure paths are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from fastapi.testclient import TestClient

from app.server import app
from app.api.auth import AuthenticatedUser
from database.audit_repository import audit_repository
from app.logging_config import StructuredJsonFormatter
from app.api.middleware import RateLimitMiddleware

client = TestClient(app)


# ── 1. Authentication & RBAC Tests ────────────────────────────────────────────

def test_public_health_and_readiness_no_auth_required():
    resp_health = client.get("/health")
    assert resp_health.status_code == 200

    resp_ready = client.get("/ready")
    assert resp_ready.status_code in (200, 503)


def test_missing_api_key_when_auth_enabled():
    with patch.dict(os.environ, {"ENABLE_API_AUTH": "true", "API_KEYS_ADMIN": "admin-secret-key-123"}):
        resp = client.post("/api/v1/jobs/rent_reminder_scan/run")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"] == "AUTHENTICATION_REQUIRED"
        assert "Missing API authentication" in data["message"]


def test_invalid_api_key_when_auth_enabled():
    with patch.dict(os.environ, {"ENABLE_API_AUTH": "true", "API_KEYS_ADMIN": "admin-secret-key-123"}):
        resp = client.post(
            "/api/v1/jobs/rent_reminder_scan/run",
            headers={"X-API-Key": "invalid-wrong-key"}
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"] == "AUTHENTICATION_REQUIRED"
        assert "Invalid API key" in data["message"]


def test_read_only_access_to_admin_endpoint_forbidden():
    with patch.dict(os.environ, {
        "ENABLE_API_AUTH": "true",
        "API_KEYS_ADMIN": "admin-secret-key-123",
        "API_KEYS_READONLY": "readonly-key-456"
    }):
        resp = client.post(
            "/api/v1/jobs/rent_reminder_scan/run",
            headers={"X-API-Key": "readonly-key-456"}
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"] == "FORBIDDEN"
        assert "requires 'admin' role" in data["message"]


def test_admin_access_to_admin_endpoint_succeeds():
    with patch.dict(os.environ, {
        "ENABLE_API_AUTH": "true",
        "API_KEYS_ADMIN": "admin-secret-key-123"
    }), patch("app.api.routers.jobs.run_registered_job", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {
            "job_name": "rent_reminder_scan",
            "status": "SUCCESS",
            "attempts": 1,
            "duration_ms": 50.0
        }
        resp = client.post(
            "/api/v1/jobs/rent_reminder_scan/run",
            headers={"X-API-Key": "admin-secret-key-123"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"


def test_bearer_token_authentication_succeeds():
    with patch.dict(os.environ, {
        "ENABLE_API_AUTH": "true",
        "API_KEYS_ADMIN": "admin-secret-key-123"
    }), patch("app.api.routers.jobs.run_registered_job", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {
            "job_name": "rent_reminder_scan",
            "status": "SUCCESS",
            "attempts": 1,
            "duration_ms": 50.0
        }
        resp = client.post(
            "/api/v1/jobs/rent_reminder_scan/run",
            headers={"Authorization": "Bearer admin-secret-key-123"}
        )
        assert resp.status_code == 200


# ── 2. Security Middleware & Abuse Protection Tests ───────────────────────────

def test_security_headers_present():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_x_request_id_header_propagated():
    custom_req_id = "req-custom-audit-test-999"
    resp = client.get("/health", headers={"X-Request-ID": custom_req_id})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == custom_req_id


def test_payload_size_limit_exceeded():
    # 3 MB content length header
    resp = client.post(
        "/api/v1/pipeline/message",
        headers={"Content-Length": str(3 * 1024 * 1024)},
        json={"channel": "api", "user_id": "test", "text": "oversized"}
    )
    assert resp.status_code == 413
    data = resp.json()
    assert data["error"] == "PAYLOAD_TOO_LARGE"


def test_rate_limit_exceeded():
    # Simulate a client exceeding 3 req/min limit
    with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "3"}), \
         patch("database.property_repository.property_repository.list_properties", new_callable=AsyncMock, return_value=[]):
        test_client = TestClient(app)
        # 3 requests pass
        for _ in range(3):
            r = test_client.get("/api/v1/properties", headers={"X-Forwarded-For": "198.51.100.1"})
            assert r.status_code == 200

        # 4th request must be rate-limited
        r4 = test_client.get("/api/v1/properties", headers={"X-Forwarded-For": "198.51.100.1"})
        assert r4.status_code == 429
        data = r4.json()
        assert data["error"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in r4.headers


# ── 3. Audit Logging Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_persists_mutation_and_redacts_secrets():
    audit_repository.clear_fallback()

    rec = await audit_repository.create_audit_log(
        action="TENANT_MANUAL_HOLD_UPDATE",
        actor="admin:admin-test-key",
        details="Toggled manual hold",
        before_state={"tenant_id": "T-100", "manual_hold": False, "api_key": "secret-token"},
        after_state={"tenant_id": "T-100", "manual_hold": True, "password": "super-secret-password"},
        request_id="req-audit-123"
    )
    assert rec["action"] == "TENANT_MANUAL_HOLD_UPDATE"
    assert rec["actor"] == "admin:admin-test-key"
    assert "[req-audit-123]" in rec["details"]

    # Verify sensitive data was redacted
    assert rec["before_state"]["api_key"] == "[REDACTED_SECRET]"
    assert rec["after_state"]["password"] == "[REDACTED_SECRET]"

    logs = await audit_repository.list_audit_logs()
    assert len(logs) == 1
    assert logs[0]["log_id"] == rec["log_id"]


# ── 4. Observability & Prometheus Metrics Tests ───────────────────────────────

def test_metrics_endpoint_returns_prometheus_format():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers.get("content-type").startswith("text/plain")
    content = resp.text
    assert "elarion_uptime_seconds" in content
    assert "http_requests_total" in content
    assert "background_job_executions_total" in content


# ── 5. Structured JSON Logging & PII Scrubbing Tests ──────────────────────────

def test_structured_json_formatter_scrubs_secrets():
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="elarion.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="User authenticated with api_key=sk-1234567890 and password=SuperSecretPassword123",
        args=(),
        exc_info=None
    )
    record.request_id = "req-1234"
    record.duration_ms = 45.2

    output = formatter.format(record)
    log_json = json.loads(output)

    assert log_json["level"] == "INFO"
    assert log_json["request_id"] == "req-1234"
    assert log_json["duration_ms"] == 45.2
    assert "SuperSecretPassword123" not in log_json["message"]
    assert "sk-1234567890" not in log_json["message"]
    assert "[REDACTED_SECRET]" in log_json["message"]
