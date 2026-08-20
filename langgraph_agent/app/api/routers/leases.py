"""
Leases Router — Phase 7 API Layer.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Security
from app.api.schemas import LeaseResponse, LeaseExpiryEventResponse
from app.api.auth import require_auth, AuthenticatedUser
from database.lease_repository import lease_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leases", tags=["Leases"])

@router.get(
    "",
    response_model=List[LeaseResponse],
    summary="List Leases",
    description="Retrieves a list of leases, optionally filtered by tenant, property, or status."
)
async def list_leases(
    tenant_id: Optional[str] = Query(None),
    property_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Security(require_auth)
) -> List[LeaseResponse]:
    try:
        leases = await lease_repository.list_leases(
            tenant_id=tenant_id, property_id=property_id, status=status_filter, limit=limit, offset=offset
        )
        return [LeaseResponse(**l) for l in leases]
    except Exception as e:
        logger.error(f"Error querying leases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query leases: {str(e)}"
        )

@router.get(
    "/expiry-events",
    response_model=List[LeaseExpiryEventResponse],
    summary="List Lease Expiry Events",
    description="Retrieves lease expiry events (e.g., 90-day, 60-day windows)."
)
async def list_expiry_events(
    lease_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Security(require_auth)
) -> List[LeaseExpiryEventResponse]:
    try:
        events = await lease_repository.list_expiry_events(
            lease_id=lease_id, status=status_filter, limit=limit, offset=offset
        )
        return [LeaseExpiryEventResponse(**e) for e in events]
    except Exception as e:
        logger.error(f"Error querying expiry events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query expiry events: {str(e)}"
        )

@router.get(
    "/{lease_id}",
    response_model=LeaseResponse,
    summary="Get Lease by ID"
)
async def get_lease(
    lease_id: str,
    user: AuthenticatedUser = Security(require_auth)
) -> LeaseResponse:
    try:
        lease = await lease_repository.get_lease_by_id(lease_id)
        if not lease:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found")
        return LeaseResponse(**lease)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lease {lease_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lease: {str(e)}"
        )
