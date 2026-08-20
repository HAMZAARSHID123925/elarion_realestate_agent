"""
Health & Readiness Router — Phase 4 API Layer.
"""
import logging
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.schemas import HealthResponse, ReadinessResponse
from database.tenant_repository import tenant_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health & Readiness"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness Probe",
    description="Returns application service liveness status."
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", service="elarion-core-api", version="2.0")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Probes PostgreSQL database connectivity to verify operational readiness."
)
async def readiness_check():
    try:
        is_ready = await tenant_repository.check_connection()
        if not is_ready:
            raise RuntimeError("Database ping returned empty result")
        return ReadinessResponse(status="ready", database="connected")
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": f"disconnected: {str(e)}"}
        )
