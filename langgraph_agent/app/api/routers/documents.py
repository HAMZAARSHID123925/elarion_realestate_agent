"""
Documents Router — Phase 7 API Layer.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Security
from app.api.schemas import DocumentResponse
from app.api.auth import require_auth, AuthenticatedUser
from database.document_repository import document_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

@router.get(
    "",
    response_model=List[DocumentResponse],
    summary="List Renewal Documents",
    description="Retrieves a list of renewal documents."
)
async def list_documents(
    lease_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Security(require_auth)
) -> List[DocumentResponse]:
    try:
        docs = await document_repository.list_documents(
            lease_id=lease_id, tenant_id=tenant_id, status=status_filter, limit=limit, offset=offset
        )
        return [DocumentResponse(**d) for d in docs]
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query documents: {str(e)}"
        )
