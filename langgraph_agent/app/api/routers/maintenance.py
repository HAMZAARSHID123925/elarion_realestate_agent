"""
Maintenance Tickets Resource Router — Phase 4 API Layer & Phase 6 RBAC/Audit.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Security, Request

from app.api.schemas import (
    TicketCreateRequest,
    TicketResponse,
    TicketDetailResponse,
    TicketStatusLogResponse,
)
from app.api.auth import require_auth, AuthenticatedUser
from database.maintenance_repository import maintenance_repository
from database.audit_repository import audit_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/maintenance", tags=["Maintenance"])


@router.get(
    "/tickets",
    response_model=List[TicketResponse],
    summary="List Maintenance Tickets",
    description="Retrieves a list of maintenance tickets with optional status and urgency filters (Requires Auth)."
)
async def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status", description="Ticket status (e.g. OPEN, ASSIGNED, RESOLVED)"),
    urgency: Optional[str] = Query(None, description="Urgency level (low, medium, high)"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    limit: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Security(require_auth)
) -> List[TicketResponse]:
    try:
        tickets = await maintenance_repository.list_tickets(
            status=status_filter,
            urgency=urgency,
            tenant_id=tenant_id,
            limit=limit
        )
        return [
            TicketResponse(
                ticket_id=t.get("ticket_id"),
                tenant_id=t.get("tenant_id"),
                property_id=t.get("property_id"),
                unit_id=t.get("unit_id"),
                category=t.get("category"),
                description=t.get("description"),
                urgency=t.get("urgency"),
                status=t.get("status", "OPEN"),
                vendor_id=t.get("vendor_id"),
                assignment_status=t.get("assignment_status", "UNASSIGNED"),
                created_at=t.get("created_at")
            )
            for t in tickets
        ]
    except Exception as e:
        logger.error(f"Error querying maintenance tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query maintenance tickets: {str(e)}"
        )


@router.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Maintenance Ticket",
    description="Directly creates a new maintenance complaint ticket (Requires Auth). Records audit log."
)
async def create_ticket(
    payload: TicketCreateRequest,
    request: Request,
    user: AuthenticatedUser = Security(require_auth)
) -> TicketResponse:
    try:
        ticket = await maintenance_repository.create_ticket(
            tenant_id=payload.tenant_id,
            property_id=payload.property_id,
            unit_id=payload.unit_id,
            category=payload.category,
            description=payload.description,
            urgency=payload.urgency,
            permission_to_enter=payload.permission_to_enter,
            pets_present=payload.pets_present,
            created_by=payload.created_by or user.key_identifier,
        )

        # Audit log creation
        request_id = getattr(request.state, "request_id", None)
        await audit_repository.create_audit_log(
            action="MAINTENANCE_TICKET_CREATE",
            actor=f"{user.role}:{user.key_identifier}",
            details=f"Created maintenance ticket {ticket.get('ticket_id')} ({payload.category}, urgency={payload.urgency}) for tenant {payload.tenant_id}",
            after_state=ticket,
            request_id=request_id
        )

        return TicketResponse(
            ticket_id=ticket.get("ticket_id"),
            tenant_id=ticket.get("tenant_id"),
            property_id=ticket.get("property_id"),
            unit_id=ticket.get("unit_id"),
            category=ticket.get("category"),
            description=ticket.get("description"),
            urgency=ticket.get("urgency"),
            status=ticket.get("status", "OPEN"),
            vendor_id=ticket.get("vendor_id"),
            assignment_status=ticket.get("assignment_status", "UNASSIGNED"),
            created_at=ticket.get("created_at")
        )
    except Exception as e:
        logger.error(f"Error creating maintenance ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create maintenance ticket: {str(e)}"
        )


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get Maintenance Ticket by ID",
    description="Retrieves a single ticket and its status transition history (Requires Auth)."
)
async def get_ticket(
    ticket_id: str,
    user: AuthenticatedUser = Security(require_auth)
) -> TicketDetailResponse:
    try:
        ticket = await maintenance_repository.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Maintenance ticket with ID '{ticket_id}' not found."
            )
        status_logs = await maintenance_repository.get_ticket_status_log(ticket_id)
        return TicketDetailResponse(
            ticket_id=ticket.get("ticket_id"),
            tenant_id=ticket.get("tenant_id"),
            property_id=ticket.get("property_id"),
            unit_id=ticket.get("unit_id"),
            category=ticket.get("category"),
            description=ticket.get("description"),
            urgency=ticket.get("urgency"),
            status=ticket.get("status", "OPEN"),
            vendor_id=ticket.get("vendor_id"),
            assignment_status=ticket.get("assignment_status", "UNASSIGNED"),
            created_at=ticket.get("created_at"),
            status_history=[
                TicketStatusLogResponse(
                    log_id=log.get("log_id"),
                    ticket_id=log.get("ticket_id"),
                    old_status=log.get("old_status"),
                    new_status=log.get("new_status"),
                    timestamp=log.get("timestamp")
                )
                for log in status_logs
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching maintenance ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ticket: {str(e)}"
        )
