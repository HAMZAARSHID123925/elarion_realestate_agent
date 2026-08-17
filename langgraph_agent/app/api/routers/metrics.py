"""
Prometheus Metrics Exporter Router — Phase 6 Observability.

Provides a standard Prometheus-compatible GET /metrics endpoint.
"""
import time
from typing import Dict
from collections import defaultdict

from fastapi import APIRouter, Response

router = APIRouter(tags=["Observability & Metrics"])

# In-memory metrics storage
_START_TIME = time.time()
_HTTP_REQUESTS: Dict[str, int] = defaultdict(int)
_HTTP_DURATIONS: Dict[str, float] = defaultdict(float)
_JOB_EXECUTIONS: Dict[str, int] = defaultdict(int)
_JOB_FAILURES: Dict[str, int] = defaultdict(int)


def record_http_request(method: str, path: str, status_code: int, duration_sec: float):
    """Records an incoming HTTP request for Prometheus aggregation."""
    # Sanitize path to avoid cardinality explosion
    normalized_path = path
    if path.startswith("/api/v1/tenants/") and path != "/api/v1/tenants":
        normalized_path = "/api/v1/tenants/{id}"
    elif path.startswith("/api/v1/properties/") and path != "/api/v1/properties":
        normalized_path = "/api/v1/properties/{id}"
    elif path.startswith("/api/v1/maintenance/tickets/") and path != "/api/v1/maintenance/tickets":
        normalized_path = "/api/v1/maintenance/tickets/{id}"
    elif path.startswith("/api/v1/jobs/") and "/run" in path:
        normalized_path = "/api/v1/jobs/{job_name}/run"

    key = f'method="{method}",path="{normalized_path}",status="{status_code}"'
    _HTTP_REQUESTS[key] += 1
    _HTTP_DURATIONS[key] += duration_sec


def record_job_metric(job_name: str, status: str, is_failure: bool = False):
    """Records background job execution metrics."""
    _JOB_EXECUTIONS[f'job_name="{job_name}",status="{status}"'] += 1
    if is_failure:
        _JOB_FAILURES[f'job_name="{job_name}"'] += 1


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Returns standard Prometheus text-format metrics for monitoring and observability."
)
async def get_metrics() -> Response:
    """
    Generates standard Prometheus exposition format.
    """
    uptime = time.time() - _START_TIME
    lines = [
        "# HELP elarion_uptime_seconds Total application uptime in seconds.",
        "# TYPE elarion_uptime_seconds gauge",
        f"elarion_uptime_seconds {uptime:.2f}",
        "",
        "# HELP http_requests_total Total number of HTTP requests processed.",
        "# TYPE http_requests_total counter"
    ]

    for labels, count in _HTTP_REQUESTS.items():
        lines.append(f"http_requests_total{{{labels}}} {count}")

    lines.extend([
        "",
        "# HELP http_request_duration_seconds_total Total duration of HTTP requests in seconds.",
        "# TYPE http_request_duration_seconds_total counter"
    ])
    for labels, total_sec in _HTTP_DURATIONS.items():
        lines.append(f"http_request_duration_seconds_total{{{labels}}} {total_sec:.4f}")

    lines.extend([
        "",
        "# HELP background_job_executions_total Total number of background job runs.",
        "# TYPE background_job_executions_total counter"
    ])
    for labels, count in _JOB_EXECUTIONS.items():
        lines.append(f"background_job_executions_total{{{labels}}} {count}")

    lines.extend([
        "",
        "# HELP background_job_failures_total Total number of failed background jobs.",
        "# TYPE background_job_failures_total counter"
    ])
    for labels, count in _JOB_FAILURES.items():
        lines.append(f"background_job_failures_total{{{labels}}} {count}")

    lines.append("")
    output = "\n".join(lines)
    return Response(content=output, media_type="text/plain; version=0.0.4")
