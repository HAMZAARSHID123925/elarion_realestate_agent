"""
Master Pipeline Ingestion Router — Phase 4 API Layer.
"""
import logging
from fastapi import APIRouter, HTTPException, status

from app.api.schemas import PipelineMessageRequest, PipelineMessageResponse
from app.pipeline import invoke_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["Master Pipeline"])


@router.post(
    "/message",
    response_model=PipelineMessageResponse,
    summary="Ingest Channel Message",
    description="Ingests a normalized user message into the master supervisor pipeline (Layer 2 Orchestrator -> Layer 3 Department Subgraph)."
)
async def process_pipeline_message(payload: PipelineMessageRequest) -> PipelineMessageResponse:
    try:
        from app.pipeline import handle_request
        final_resp = await handle_request(
            channel=payload.channel,
            user_id=payload.user_id,
            raw_text=payload.text,
            channel_metadata=payload.channel_metadata or {}
        )

        return PipelineMessageResponse(
            channel=payload.channel,
            user_id=payload.user_id,
            final_response=final_resp,
            intent="Processed",
            active_department="orchestrator"
        )
    except Exception as e:
        logger.error(f"Error processing pipeline message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline processing failed: {str(e)}"
        )

