"""
Workflow Triggers and Execution Router — Phase 4 API Layer & Phase 6 RBAC/Audit.
"""
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status, Security, Request

from app.api.schemas import (
    RentReminderRunResponse,
    RentReminderEvaluateRequest,
    RentReminderEvaluateResponse,
    LeaseExpiryScanResponse,
    RenewalReminderScanResponse,
)
from app.api.auth import require_service_or_admin, AuthenticatedUser
from app.core_workflows.rent_reminder.scheduler import run_daily_rent_reminder_workflow
from app.core_workflows.rent_reminder.graph import rent_reminder_graph
from app.core_workflows.rent_renewal.lease_expiry.scheduler_entry import run_lease_expiry_scan
from app.core_workflows.rent_renewal.renewal_reminder.service import run_renewal_reminder_dispatch
from database.audit_repository import audit_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])


@router.post(
    "/rent-reminder/run",
    response_model=RentReminderRunResponse,
    summary="Trigger Daily Rent Reminder Scan",
    description="Executes automated batch scan of overdue rent records (Admin/Service Only)."
)
async def trigger_rent_reminder_batch(
    request: Request,
    current_date: Optional[str] = Query(None, description="Reference date YYYY-MM-DD (defaults to today)"),
    user: AuthenticatedUser = Security(require_service_or_admin)
) -> RentReminderRunResponse:
    request_id = getattr(request.state, "request_id", None)
    try:
        summary = await asyncio.to_thread(run_daily_rent_reminder_workflow, current_date)

        # Audit log creation
        await audit_repository.create_audit_log(
            action="WORKFLOW_TRIGGER_RENT_REMINDER",
            actor=f"{user.role}:{user.key_identifier}",
            details=f"Triggered rent reminder batch scan. Scanned: {summary.get('records_scanned', 0)}, Reminders: {summary.get('reminders_sent', 0)}",
            after_state=summary,
            request_id=request_id
        )

        return RentReminderRunResponse(
            status="completed",
            records_scanned=summary.get("records_scanned", 0),
            reminders_sent=summary.get("reminders_sent", 0),
            followups_sent=summary.get("followups_sent", 0),
            escalated=summary.get("escalated", 0),
            skipped=summary.get("skipped", 0),
            errors=[]
        )
    except Exception as e:
        logger.error(f"Error running rent reminder batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute rent reminder batch: {str(e)}"
        )


@router.post(
    "/rent-reminder/evaluate",
    response_model=RentReminderEvaluateResponse,
    summary="Evaluate Single Tenant Reminder",
    description="Directly evaluates and executes rent reminder rules for a single tenant ID (Admin/Service Only)."
)
async def evaluate_single_tenant_reminder(
    payload: RentReminderEvaluateRequest,
    request: Request,
    user: AuthenticatedUser = Security(require_service_or_admin)
) -> RentReminderEvaluateResponse:
    request_id = getattr(request.state, "request_id", None)
    try:
        initial_state = {
            "tenant_id": payload.tenant_id,
            "current_date": payload.current_date,
            "logs": []
        }
        # Execute rent reminder graph
        final_state = await asyncio.to_thread(rent_reminder_graph.invoke, initial_state)

        await audit_repository.create_audit_log(
            action="WORKFLOW_EVALUATE_TENANT_REMINDER",
            actor=f"{user.role}:{user.key_identifier}",
            details=f"Evaluated tenant {payload.tenant_id}. Action: {final_state.get('action')}",
            after_state={"tenant_id": payload.tenant_id, "action": final_state.get("action")},
            request_id=request_id
        )

        return RentReminderEvaluateResponse(
            tenant_id=payload.tenant_id,
            action=final_state.get("action", "UNKNOWN"),
            last_reminder_status=final_state.get("last_reminder_status", "none"),
            days_overdue=final_state.get("days_overdue", 0),
            rent_amount=float(final_state.get("rent_amount") or 0.0),
            logs=final_state.get("logs", []),
            error=final_state.get("error")
        )
    except Exception as e:
        logger.error(f"Error evaluating tenant {payload.tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate rent reminder for tenant: {str(e)}"
        )


@router.post(
    "/lease-expiry/scan",
    response_model=LeaseExpiryScanResponse,
    summary="Trigger Lease Expiry Scan",
    description="Executes daily proactive scan for leases approaching expiry windows (Admin/Service Only)."
)
async def trigger_lease_expiry_scan(
    request: Request,
    user: AuthenticatedUser = Security(require_service_or_admin)
) -> LeaseExpiryScanResponse:
    request_id = getattr(request.state, "request_id", None)
    try:
        summary = await run_lease_expiry_scan(trigger_type="manual_api")
        if summary.get("status") == "FAILED":
            raise RuntimeError(summary.get("error", "Unknown error in lease expiry scan"))

        await audit_repository.create_audit_log(
            action="WORKFLOW_TRIGGER_LEASE_EXPIRY_SCAN",
            actor=f"{user.role}:{user.key_identifier}",
            details=f"Triggered lease expiry scan. Scanned: {summary.get('leases_scanned', 0)}, Events: {summary.get('events_created', 0)}",
            after_state=summary,
            request_id=request_id
        )

        return LeaseExpiryScanResponse(
            status="completed",
            scanned=summary.get("leases_scanned", 0),
            events_created=summary.get("events_created", 0),
            run_id=str(summary.get("run_id", "run-api"))
        )
    except Exception as e:
        logger.error(f"Error running lease expiry scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute lease expiry scan: {str(e)}"
        )


@router.post(
    "/renewal-reminder/scan",
    response_model=RenewalReminderScanResponse,
    summary="Trigger Renewal Reminder Scan",
    description="Executes daily proactive dispatch of renewal reminders (Admin/Service Only)."
)
async def trigger_renewal_reminder_scan(
    request: Request,
    user: AuthenticatedUser = Security(require_service_or_admin)
) -> RenewalReminderScanResponse:
    request_id = getattr(request.state, "request_id", None)
    try:
        summary = await run_renewal_reminder_dispatch()
        if summary.get("status") == "FAILED":
            raise RuntimeError(summary.get("error", "Unknown error in renewal reminder scan"))

        await audit_repository.create_audit_log(
            action="WORKFLOW_TRIGGER_RENEWAL_REMINDER_SCAN",
            actor=f"{user.role}:{user.key_identifier}",
            details=f"Triggered renewal reminder scan. Scanned: {summary.get('events_scanned', 0)}, Sent: {summary.get('reminders_sent', 0)}",
            after_state=summary,
            request_id=request_id
        )

        return RenewalReminderScanResponse(
            status="completed",
            scanned=summary.get("events_scanned") if summary.get("events_scanned") is not None else summary.get("pending_events_scanned", 0),
            reminders_sent=summary.get("reminders_sent", 0),
            run_id=str(summary.get("run_id", "run-api"))
        )
    except Exception as e:
        logger.error(f"Error running renewal reminder scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute renewal reminder scan: {str(e)}"
        )
