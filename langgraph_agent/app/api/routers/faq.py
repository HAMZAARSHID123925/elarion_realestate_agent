"""
FAQ & Property Search Router — Phase 4 API Layer.
"""
import logging
from fastapi import APIRouter, HTTPException, status
from langchain_core.messages import HumanMessage

from app.api.schemas import FAQQueryRequest, FAQQueryResponse
from app.core_workflows.faq.graph import faq_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/faq", tags=["FAQ & Search"])


@router.post(
    "/query",
    response_model=FAQQueryResponse,
    summary="Submit FAQ / Property Inquiry",
    description="Submits a tenant policy question or property search query directly to the FAQ/Search LangGraph workflow."
)
async def query_faq(payload: FAQQueryRequest) -> FAQQueryResponse:
    try:
        user_id = payload.user_id or "api_user"
        initial_state = {
            "messages": [HumanMessage(content=payload.query)],
            "missing_property_fields": []
        }
        config = {"configurable": {"thread_id": f"faq_api:{user_id}"}}

        result_state = await faq_graph.ainvoke(initial_state, config=config)
        answer = result_state.get("final_response") or "I was unable to find an answer to your inquiry."

        return FAQQueryResponse(
            query=payload.query,
            answer=answer,
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Error querying FAQ workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process FAQ inquiry: {str(e)}"
        )
