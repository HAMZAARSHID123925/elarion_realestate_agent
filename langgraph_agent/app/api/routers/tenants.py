"""
Tenants Resource Router — Phase 4 API Layer & Phase 6 RBAC/Audit.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Security, Request

from app.api.schemas import (
    TenantSummaryResponse,
    TenantDetailResponse,
    ManualHoldRequest,
    ManualHoldResponse,
)
from app.api.auth import require_auth, require_service_or_admin, AuthenticatedUser
from database.tenant_repository import tenant_repository
from database.audit_repository import audit_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenants"])


@router.get(
    "",
    response_model=List[TenantSummaryResponse],
    summary="List Tenants",
    description="Retrieves a list of tenants, optionally filtered by overdue status (Requires Auth)."
)
async def list_tenants(
    ref_date: Optional[str] = Query(None, description="Reference date YYYY-MM-DD for overdue calculation"),
    overdue_only: bool = Query(True, description="Filter for tenants whose rent is unpaid and overdue"),
    user: AuthenticatedUser = Security(require_auth)
) -> List[TenantSummaryResponse]:
    try:
        tenants = await tenant_repository.get_unpaid_overdue_tenants(ref_date)
        return [
            TenantSummaryResponse(
                tenant_id=t.get("tenant_id"),
                tenant_name=t.get("tenant_name") or t.get("name"),
                property_address=t.get("property_address"),
                rent_due_date=str(t.get("rent_due_date")) if t.get("rent_due_date") else None,
                rent_amount=float(t.get("rent_amount") or 0.0),
                payment_status=t.get("payment_status"),
                manual_hold=bool(t.get("manual_hold", False)),
                last_reminder_status=t.get("last_reminder_status", "none")
            )
            for t in tenants
        ]
    except Exception as e:
        logger.error(f"Error querying tenants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query tenants: {str(e)}"
        )


@router.get(
    "/{tenant_id}",
    response_model=TenantDetailResponse,
    summary="Get Tenant by ID",
    description="Retrieves detailed profile, rent status, and reminder timestamps for a tenant (Requires Auth)."
)
async def get_tenant(
    tenant_id: str,
    user: AuthenticatedUser = Security(require_auth)
) -> TenantDetailResponse:
    try:
        tenant = await tenant_repository.get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID '{tenant_id}' not found."
            )
        return TenantDetailResponse(
            tenant_id=tenant.get("tenant_id"),
            property_id=tenant.get("property_id"),
            unit_id=tenant.get("unit_id"),
            tenant_name=tenant.get("tenant_name") or tenant.get("name"),
            tenant_phone=tenant.get("tenant_phone"),
            phone_or_email=tenant.get("phone_or_email"),
            property_address=tenant.get("property_address"),
            rent_due_date=str(tenant.get("rent_due_date")) if tenant.get("rent_due_date") else None,
            last_payment_date=str(tenant.get("last_payment_date")) if tenant.get("last_payment_date") else None,
            rent_amount=float(tenant.get("rent_amount") or 0.0),
            payment_status=tenant.get("payment_status"),
            reminder_30_sent_at=str(tenant.get("reminder_30_sent_at")) if tenant.get("reminder_30_sent_at") else None,
            reminder_5_sent_at=str(tenant.get("reminder_5_sent_at")) if tenant.get("reminder_5_sent_at") else None,
            response_received=bool(tenant.get("response_received", False)),
            human_escalated=bool(tenant.get("human_escalated", False)),
            escalation_reason=tenant.get("escalation_reason"),
            manual_hold=bool(tenant.get("manual_hold", False)),
            last_reminder_status=tenant.get("last_reminder_status", "none"),
            created_at=tenant.get("created_at"),
            updated_at=tenant.get("updated_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tenant: {str(e)}"
        )


@router.post(
    "/{tenant_id}/hold",
    response_model=ManualHoldResponse,
    summary="Toggle Manual Hold",
    description="Sets or clears manual hold override to suppress automated rent reminders (Admin/Service Only)."
)
async def set_tenant_manual_hold(
    tenant_id: str,
    payload: ManualHoldRequest,
    request: Request,
    user: AuthenticatedUser = Security(require_service_or_admin)
) -> ManualHoldResponse:
    try:
        tenant = await tenant_repository.get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID '{tenant_id}' not found."
            )

        old_hold = bool(tenant.get("manual_hold", False))
        await tenant_repository.set_manual_hold(tenant_id, payload.manual_hold)

        # Audit log creation
        request_id = getattr(request.state, "request_id", None)
        await audit_repository.create_audit_log(
            action="TENANT_MANUAL_HOLD_UPDATE",
            actor=f"{user.role}:{user.key_identifier}",
            details=f"Updated manual hold on tenant {tenant_id} from {old_hold} to {payload.manual_hold}",
            before_state={"tenant_id": tenant_id, "manual_hold": old_hold},
            after_state={"tenant_id": tenant_id, "manual_hold": payload.manual_hold},
            request_id=request_id
        )

        action_str = "enabled (reminders suppressed)" if payload.manual_hold else "disabled (reminders active)"
        return ManualHoldResponse(
            tenant_id=tenant_id,
            manual_hold=payload.manual_hold,
            message=f"Manual hold {action_str} for tenant {tenant_id}."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating manual hold for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update manual hold: {str(e)}"
        )
