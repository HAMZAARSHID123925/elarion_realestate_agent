"""
Dashboard Router — Phase 7 API Layer.
"""
import logging
from fastapi import APIRouter, HTTPException, status, Security
from app.api.schemas import DashboardMetricsResponse
from app.api.auth import require_auth, AuthenticatedUser
from database.dashboard_repository import dashboard_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

@router.get(
    "/metrics",
    response_model=DashboardMetricsResponse,
    summary="Get Dashboard Metrics",
    description="Retrieves aggregate metrics for the dashboard overview."
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
