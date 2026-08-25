"""
Dashboard Router — Core UI REST API Layer.

Exposes REST endpoints for Overview, Conversations, Chat Transcripts,
Automations Grid, and Agent Activity.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Query, Security

from app.api.schemas import (
    DashboardMetricsResponse,
    OverviewDashboardResponse,
    ConversationsListResponse,
    ConversationDetailSchema,
    AutomationCardSchema,
    AutomationUpdateRequest,
    AutomationCreateRequest,
    AgentActivityResponse
)
from app.api.auth import require_auth, AuthenticatedUser
from database.dashboard_repository import dashboard_repository
from database.conversation_repository import conversation_repository
from database.automation_repository import automation_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get(
    "/metrics",
    response_model=DashboardMetricsResponse,
    summary="Get Legacy Dashboard Metrics"
)
async def get_dashboard_metrics(
    user: AuthenticatedUser = Security(require_auth)
) -> DashboardMetricsResponse:
    try:
        metrics = await dashboard_repository.get_overview_metrics()
        return DashboardMetricsResponse(**metrics)
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard metrics: {str(e)}"
        )


@router.get(
    "/overview",
    response_model=OverviewDashboardResponse,
    summary="Get Overview Dashboard Payload (Screenshot 0)"
)
async def get_overview_dashboard(
    user: AuthenticatedUser = Security(require_auth)
) -> OverviewDashboardResponse:
    try:
        data = await dashboard_repository.get_full_overview_data()
        return OverviewDashboardResponse(**data)
    except Exception as e:
        logger.error(f"Error fetching overview dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch overview payload: {str(e)}"
        )


@router.get(
    "/conversations",
    response_model=ConversationsListResponse,
    summary="List Conversations with Filters (Screenshot 1)"
)
async def list_conversations(
    search: Optional[str] = Query(None, description="Search name, ID, or property"),
    property_id: Optional[str] = Query(None, description="Filter by property ID"),
    unit_id: Optional[str] = Query(None, description="Filter by unit ID"),
    channel: Optional[str] = Query(None, description="Filter by channel (WhatsApp, Email, Voice, Web)"),
    intent: Optional[str] = Query(None, description="Filter by classified intent"),
    urgency: Optional[str] = Query(None, description="Filter by urgency level"),
    status: Optional[str] = Query(None, description="Filter by conversation status"),
    date_from: Optional[datetime] = Query(None, description="Filter conversations on or after this ISO datetime"),
    limit: int = Query(10, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Security(require_auth)
) -> ConversationsListResponse:
    try:
        res = await conversation_repository.list_conversations(
            search=search,
            property_id=property_id,
            unit_id=unit_id,
            channel=channel,
            intent=intent,
            urgency=urgency,
            status=status,
            date_from=date_from,
            limit=limit,
            offset=offset
        )
        return ConversationsListResponse(**res)
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailSchema,
    summary="Get Conversation Detail & Chat Transcript (Screenshot 2)"
)
async def get_conversation_detail(
    conversation_id: str,
    user: AuthenticatedUser = Security(require_auth)
) -> ConversationDetailSchema:
    try:
        conv = await conversation_repository.get_conversation_detail(conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation #{conversation_id} not found."
            )
        return ConversationDetailSchema(**conv)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation detail for {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation detail: {str(e)}"
        )


@router.post(
    "/conversations/{conversation_id}/review",
    summary="Mark Conversation Reviewed"
)
async def mark_conversation_reviewed(
    conversation_id: str,
    user: AuthenticatedUser = Security(require_auth)
) -> Dict[str, Any]:
    try:
        ok = await conversation_repository.mark_reviewed(conversation_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation #{conversation_id} not found."
            )
        return {"status": "success", "conversation_id": conversation_id, "is_reviewed": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking conversation reviewed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}"
        )


@router.get(
    "/automations",
    response_model=List[AutomationCardSchema],
    summary="List Automations Grid Rules (Screenshot 3)"
)
async def list_automations(
    user: AuthenticatedUser = Security(require_auth)
) -> List[AutomationCardSchema]:
    try:
        rules = await dashboard_repository.get_automations_list()
        return [AutomationCardSchema(**r) for r in rules]
    except Exception as e:
        logger.error(f"Error listing automations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch automations: {str(e)}"
        )


@router.get(
    "/automations/{automation_id}",
    response_model=AutomationCardSchema,
    summary="Get Automation Configuration Details"
)
async def get_automation_detail(
    automation_id: str,
    user: AuthenticatedUser = Security(require_auth)
) -> AutomationCardSchema:
    try:
        auto = await automation_repository.get_automation_by_id(automation_id)
        if not auto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automation '{automation_id}' not found."
            )
        return AutomationCardSchema(**auto)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching automation '{automation_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch automation detail: {str(e)}"
        )


@router.patch(
    "/automations/{automation_id}",
    summary="Update Automation Configuration (Persisted to PostgreSQL & Audit Logged)"
)
async def update_automation(
    automation_id: str,
    payload: AutomationUpdateRequest,
    user: AuthenticatedUser = Security(require_auth)
) -> Dict[str, Any]:
    """
    Accepts a JSON body with optional fields:
      - active (bool): toggle automation on/off ('Active' / 'Inactive')
      - escalation_conditions (List[str]): updated escalation rules text
      - channels (List[str]): updated channels list
      - name (str), description (str), scope (str)

    Persists directly to PostgreSQL database and creates an audit log record.
    """
    try:
        updates = payload.dict(exclude_unset=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update fields provided."
            )

        actor_name = getattr(user, "key_identifier", "property_manager") or "property_manager"
        updated_record = await automation_repository.update_automation(
            automation_id=automation_id,
            updates=updates,
            actor=actor_name
        )

        if not updated_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automation '{automation_id}' not found."
            )

        return {
            "status": "success",
            "automation_id": automation_id,
            "data": updated_record,
            "message": f"Automation '{automation_id}' updated and persisted to PostgreSQL database successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating automation '{automation_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update automation: {str(e)}"
        )


@router.post(
    "/automations",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create a New Automation Configuration (Persisted to PostgreSQL & Audit Logged)"
)
async def create_automation(
    payload: AutomationCreateRequest,
    user: AuthenticatedUser = Security(require_auth)
) -> Dict[str, Any]:
    try:
        data = payload.dict(exclude_unset=True)
        actor_name = getattr(user, "key_identifier", "property_manager") or "property_manager"
        created_record = await automation_repository.create_automation(
            data=data,
            actor=actor_name
        )
        return {
            "status": "success",
            "automation_id": created_record["id"],
            "data": created_record,
            "message": f"Automation '{created_record['name']}' created and persisted to PostgreSQL database successfully."
        }
    except Exception as e:
        logger.error(f"Error creating automation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create automation: {str(e)}"
        )


@router.delete(
    "/automations/{automation_id}",
    summary="Delete Automation Configuration (Persisted to PostgreSQL & Audit Logged)"
)
async def delete_automation(
    automation_id: str,
    user: AuthenticatedUser = Security(require_auth)
) -> Dict[str, Any]:
    try:
        actor_name = getattr(user, "key_identifier", "property_manager") or "property_manager"
        deleted = await automation_repository.delete_automation(
            automation_id=automation_id,
            actor=actor_name
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automation '{automation_id}' not found or could not be deleted."
            )
        return {
            "status": "success",
            "automation_id": automation_id,
            "message": f"Automation '{automation_id}' deleted and removed from PostgreSQL database successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting automation '{automation_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete automation: {str(e)}"
        )


@router.get(
    "/agent-activity",
    response_model=AgentActivityResponse,
    summary="Get Agent Activity Metrics & Log Feed (Screenshot 4)"
)
async def get_agent_activity(
    period: str = Query("today", description="Time period filter: today | yesterday | 7days"),
    user: AuthenticatedUser = Security(require_auth)
) -> AgentActivityResponse:
    try:
        data = await dashboard_repository.get_agent_activity_metrics(period=period)
        return AgentActivityResponse(**data)
    except Exception as e:
        logger.error(f"Error fetching agent activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agent activity: {str(e)}"
        )

