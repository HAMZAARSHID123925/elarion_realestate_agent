"""
Renewals Router — Phase 7 API Layer.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Security
from app.api.schemas import RenewalReminderResponse, RenewalIntentResponse
from app.api.auth import require_auth, AuthenticatedUser
from database.renewal_repository import renewal_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/renewals", tags=["Renewals"])

@router.get(
    "/reminders",
    response_model=List[RenewalReminderResponse],
    summary="List Renewal Reminders",
    description="Retrieves a list of sent renewal reminders."
)
async def list_renewal_reminders(
    lease_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Security(require_auth)
) -> List[RenewalReminderResponse]:
    try:
        reminders = await renewal_repository.list_renewal_reminders(
            lease_id=lease_id, tenant_id=tenant_id, limit=limit, offset=offset
        )
        return [RenewalReminderResponse(**r) for r in reminders]
    except Exception as e:
        logger.error(f"Error querying renewal reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query renewal reminders: {str(e)}"
        )

@router.get(
    "/intents",
    response_model=List[RenewalIntentResponse],
    summary="List Renewal Intents",
    description="Retrieves tenant renewal intents."
)
async def list_renewal_intents(
    lease_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    intent: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Security(require_auth)
) -> List[RenewalIntentResponse]:
    try:
        intents = await renewal_repository.list_renewal_intents(
            lease_id=lease_id, tenant_id=tenant_id, intent=intent, limit=limit, offset=offset
        )
        return [RenewalIntentResponse(**i) for i in intents]
    except Exception as e:
        logger.error(f"Error querying renewal intents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query renewal intents: {str(e)}"
        )
