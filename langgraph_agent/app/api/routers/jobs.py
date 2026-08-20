"""
Background Jobs & Alerting Operational Router — Phase 5 & Phase 6 Security.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Security, Request

from app.api.schemas import (
    JobInfoResponse,
    JobRunResponse,
    DeadLetterRecordResponse,
    AlertRecordResponse,
)
from app.api.auth import require_admin, require_auth, AuthenticatedUser
from app.jobs.registry import JOB_REGISTRY, run_registered_job
from app.jobs.runner import job_runner
from app.jobs.locks import job_lock_manager
from app.jobs.alerts import alert_service
from database.audit_repository import audit_repository
from app.api.routers.metrics import record_job_metric

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["Background Jobs & Alerts"])


@router.get(
    "",
    response_model=List[JobInfoResponse],
    summary="List Registered Background Jobs",
    description="Retrieves all registered recurring background jobs, cadences, lock state, and last execution telemetry."
)
async def list_jobs(
    user: AuthenticatedUser = Security(require_auth)
) -> List[JobInfoResponse]:
    try:
        jobs_list = []
        for name, info in JOB_REGISTRY.items():
            last_run = job_runner.get_telemetry(name)
            is_locked = job_lock_manager.is_locked(name)
            jobs_list.append(
                JobInfoResponse(
                    job_name=name,
                    description=info.get("description", ""),
                    domain=info.get("domain", "Platform"),
                    default_cadence=info.get("default_cadence", "Unknown"),
                    is_locked=is_locked,
                    last_run=last_run
                )
            )
        return jobs_list
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list background jobs: {str(e)}"
        )


@router.post(
    "/{job_name}/run",
    response_model=JobRunResponse,
    summary="Trigger Registered Job",
    description="Immediately executes a registered background job (Admin Only). Records audit log and telemetry."
)
async def trigger_job(
    job_name: str,
    request: Request,
    user: AuthenticatedUser = Security(require_admin)
) -> JobRunResponse:
    if job_name not in JOB_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Background job '{job_name}' is not registered. Valid jobs: {list(JOB_REGISTRY.keys())}"
        )

    request_id = getattr(request.state, "request_id", None)

    try:
        telemetry = await run_registered_job(job_name)
        status_val = telemetry.get("status", "UNKNOWN")

        # Record metric
        record_job_metric(job_name, status_val, is_failure=(status_val == "DEAD_LETTER"))

        # Create audit log
        await audit_repository.create_audit_log(
            action="JOB_TRIGGER_MANUAL",
            actor=f"{user.role}:{user.key_identifier}",
            details=f"Manually triggered background job '{job_name}'. Status: {status_val}",
            after_state=telemetry,
            request_id=request_id
        )

        return JobRunResponse(
            job_name=job_name,
            status=status_val,
            attempts=telemetry.get("attempts", 1),
            duration_ms=telemetry.get("duration_ms"),
            result_summary=telemetry.get("result_summary"),
            error=telemetry.get("error_message") or telemetry.get("error")
        )
    except Exception as e:
        logger.error(f"Error executing job '{job_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute job '{job_name}': {str(e)}"
        )


@router.get(
    "/dead-letter",
    response_model=List[DeadLetterRecordResponse],
    summary="List Dead-Letter Jobs",
    description="Retrieves failed background jobs from the Dead-Letter Queue (Admin Only)."
)
async def list_dead_letter_jobs(
    limit: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Security(require_admin)
) -> List[DeadLetterRecordResponse]:
    records = await job_runner.get_dead_letter_records(limit=limit)
    return [
        DeadLetterRecordResponse(
            dead_letter_id=r.get("dead_letter_id", ""),
            job_name=r.get("job_name", ""),
            status=r.get("status", "DEAD_LETTER"),
            attempts=r.get("attempts", 0),
            started_at=r.get("started_at", ""),
            failed_at=r.get("failed_at", ""),
            duration_ms=r.get("duration_ms", 0.0),
            error_type=r.get("error_type", ""),
            error_message=r.get("error_message", "")
        )
        for r in records
    ]


@router.get(
    "/alerts",
    response_model=List[AlertRecordResponse],
    summary="List High-Priority Alerts",
    description="Retrieves recent operational alerts (Requires Auth)."
)
async def list_alerts(
    limit: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Security(require_auth)
) -> List[AlertRecordResponse]:
    alerts = alert_service.get_recent_alerts(limit=limit)
    return [
        AlertRecordResponse(
            alert_id=a.get("alert_id", ""),
            alert_type=a.get("alert_type", ""),
            severity=a.get("severity", "INFO"),
            message=a.get("message", ""),
            metadata=a.get("metadata", {}),
            dispatched_at=a.get("dispatched_at", ""),
            status=a.get("status", "DISPATCHED")
        )
        for a in alerts
    ]
