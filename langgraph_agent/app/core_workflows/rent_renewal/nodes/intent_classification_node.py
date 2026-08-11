"""
Intent Classification Node — Phase 3, Workflow #4.

Interprets the tenant's natural language response regarding their lease renewal,
classifies the intent (YES, NO, UNCLEAR, NEGOTIATION), and persists the decision.
"""
import logging
from typing import Dict, Any

from app.core_workflows.rent_renewal.state import RentRenewalState
from app.core_workflows.rent_renewal.renewal_intent.classifier import classify_renewal_intent
from app.core_workflows.rent_renewal.renewal_intent.repository import record_renewal_intent

logger = logging.getLogger(__name__)


async def intent_classification_node(state: RentRenewalState) -> Dict[str, Any]:
    """
    NODE: intent_classification_node
    Extracts renewal intent from tenant response.
    """
    logs = state.get("logs", [])
    tenant_response = state.get("tenant_response")

    # If tenant_response not in top-level state, check the last message
    if not tenant_response:
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                tenant_response = last_msg.content
            elif isinstance(last_msg, dict):
                tenant_response = last_msg.get("content", "")

    tenant_response = tenant_response or ""
    lease_id = state.get("lease_id") or "L-UNKNOWN"
    tenant_id = state.get("tenant_id") or "T-UNKNOWN"

    lease_context = {
        "lease_id": lease_id,
        "tenant_id": tenant_id,
        "property_address": state.get("property_address"),
        "current_rent": state.get("monthly_rent"),
        "lease_end_date": state.get("lease_end_date"),
    }

    # Classify intent
    result = await classify_renewal_intent(tenant_response, lease_context)
    intent = result.intent
    confidence = result.confidence
    reasoning = result.reasoning

    # Map intent to renewal_status
    if intent == "YES":
        new_status = "PENDING_MANAGER_REVIEW"
    elif intent == "NO":
        new_status = "TENANT_DECLINED"
    elif intent == "NEGOTIATION":
        new_status = "PENDING_MANAGER_REVIEW"
    else:  # UNCLEAR
        new_status = "CLARIFICATION_REQUIRED"

    # Persist intent in DB if valid lease_id exists
    try:
        if lease_id and lease_id != "L-UNKNOWN":
            await record_renewal_intent(
                lease_id=lease_id,
                tenant_id=tenant_id,
                tenant_response=tenant_response,
                intent=intent,
                confidence=confidence,
                reasoning=reasoning,
                renewal_status=new_status,
                requested_term=result.requested_term_months,
                proposed_rent=result.proposed_rent,
            )
    except Exception as e:
        logger.warning("Could not persist renewal intent to DB: %s", e)

    logs.append(
        f"[intent_classification_node] Classified intent='{intent}' (conf={confidence:.2f}) "
        f"for tenant {tenant_id}. Status -> {new_status}"
    )

    return {
        "tenant_response": tenant_response,
        "renewal_intent": intent,
        "intent_confidence": confidence,
        "intent_reasoning": reasoning,
        "renewal_status": new_status,
        "requested_term_months": result.requested_term_months,
        "proposed_rent": result.proposed_rent,
        "logs": logs,
    }
