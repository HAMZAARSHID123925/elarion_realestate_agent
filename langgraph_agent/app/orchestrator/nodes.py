import json
import logging
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from app.orchestrator.state import OrchestratorState
from app.orchestrator.schemas import UnifiedResponse
from app.orchestrator.rate_limiter import groq_queue
# Same MCP client singleton the maintenance workflow already uses for
# lookup_tenant / create_ticket / assign_vendor -- it is connected once at
# process startup by whatsapp_server.py / vapi_server.py, so reusing it here
# avoids opening a second stdio connection to mcp_server.py.
from app.core_workflows.maintenance.mcp_client import mcp_client

logger = logging.getLogger(__name__)

# Initialize LLM
def get_llm():
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# --- Pydantic Schema for Unified Structured Output ---

class ClassificationResult(BaseModel):
    intent: Literal["maintenance", "leasing", "billing", "faq", "general"] = Field(
        description="The primary intent of the user's message. Use 'faq' for informational "
                    "questions about policies, processes, or the property (e.g. 'what's the "
                    "rent payment process', 'what are the pool hours') that are not themselves "
                    "a maintenance issue, a lease/billing transaction, or a general inquiry."
    )
    urgency: Literal["high", "medium", "low"] = Field(
        description="The urgency of the request. 'high' should only be used for active danger or ongoing damage (e.g., active leak, fire)."
    )
    entities: Dict[str, str] = Field(
        description="Relevant details as string key-value pairs (e.g., {'location': 'kitchen', 'issue': 'burst pipe', 'budget': '200 lakhs'}). Empty if nothing to extract."
    )

# --- Async Nodes ---

async def identification_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Identifies the user from the real tenant database via the maintenance MCP
    server's lookup_tenant tool (same DB the maintenance workflow already uses).
    Fail-closed implementation: defaults to unknown/guest unless a strict match is found,
    and any DB/connection error also falls back to guest rather than raising --
    identification must never crash the pipeline.
    """
    user_id = state["request"].user_id

    tenant = None
    try:
        result_json = await mcp_client.call_tool("lookup_tenant", {"phone_or_email": user_id})
        result = json.loads(result_json) if result_json else {}
        if "error" not in result:
            tenant = {
                "id": result.get("tenant_id"),
                "role": "tenant",
                "property_id": result.get("property_id"),
            }
    except Exception as e:
        # Not connected yet, DB hiccup, etc. -- fail closed to guest, never raise here.
        logger.error(f"identification_node: lookup_tenant failed for {user_id}: {e}")
        tenant = None

    if tenant is None:
        profile = {
            "status": "unknown",
            "role": "guest",
            "user_id": user_id,
            "property_id": None
        }
        logger.info(f"Identified User: Guest (unknown) — {user_id}")
    else:
        profile = {
            "status": "known",
            "role": tenant["role"],
            "user_id": tenant["id"],
            "property_id": tenant["property_id"]
        }
        logger.info(f"Identified User: Registered {tenant['role']} ({tenant['id']})")
    
    return {"user_profile": profile}

async def classify_and_extract_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Consolidated node that classifies intent, assesses urgency, and extracts entities 
    in a SINGLE LLM call to reduce latency. Includes fail-safe fallbacks.
    """
    llm = get_llm()
    request = state["request"]
    
    prompt = f"""Analyze this message from a property management channel.
Message: "{request.raw_text}"

Return:
- intent: one of maintenance, leasing, billing, faq, general
  (use 'faq' for informational questions about policies, processes, or the property
  that are not themselves a maintenance issue, a lease/billing transaction, or a general inquiry)
- urgency: high, medium, or low (high = active danger/damage happening now)
- entities: relevant details as key-value pairs (issue type, location, budget, timeframe, etc.)
"""
    
    try:
        # Wrap the async LLM call in our rate limiter queue
        result = await groq_queue.call(
            llm.with_structured_output(ClassificationResult).ainvoke, 
            prompt
        )
        logger.info(f"Classified: {result.intent} | Urgency: {result.urgency}")
        
        return {
            "intent": result.intent,
            "urgency": result.urgency,
            "entities": result.entities
        }
    except Exception as e:
        logger.error(f"Classification LLM failed: {e}")
        # FAIL-SAFE: don't conflate "we couldn't classify this" with "this is a real
        # emergency" -- those need different handling downstream. rules_engine_node
        # checks `error` explicitly and routes this to a distinct review action
        # instead of auto-escalating it as if urgency were genuinely high.
        return {
            "intent": "general",
            "urgency": "medium",
            "entities": {},
            "error": "classification_failed"
        }

async def rules_engine_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Applies business rules to determine the final action based on intent and urgency.
    Routes maintenance, FAQ, and rent renewal directly to their respective Layer 3 subgraphs.
    """
    intent = state.get("intent", "general")
    urgency = state.get("urgency", "medium")
    classification_failed = state.get("error") == "classification_failed"
    
    action_taken = "need_more_info"
    response_msg = "Your request has been received."
    
    if classification_failed:
        action_taken = "needs_human_review"
        response_msg = "I had a little trouble understanding that. Let me connect you with a team member."
    elif urgency == "high":
        action_taken = "human_escalation"
        response_msg = "This sounds like an emergency. I am escalating this to a live human manager immediately. Please stay on the line."
    elif intent == "maintenance":
        action_taken = "routed_to_maintenance_workflow"
        response_msg = "I have logged your maintenance request. The maintenance team will be notified."
    elif intent == "faq" or intent == "billing":
        action_taken = "routed_to_faq_workflow"
        response_msg = "Let me find that information for you."
    elif intent in ("rent_renewal", "lease_renewal"):
        action_taken = "routed_to_rent_renewal_workflow"
        response_msg = "I will connect you with our rent renewal department."
    elif intent == "leasing":
        action_taken = "routed_to_leasing_workflow"
        response_msg = "I will connect you with our leasing department."
    else:
        action_taken = "general_inquiry"
        response_msg = "Hello! Welcome to Elarion Real Estate Support. How can I assist you today with a maintenance request, lease renewal, or property inquiry?"

        
    # If the user sent empty text, override
    if not state["request"].raw_text.strip():
        action_taken = "needs_more_info"
        response_msg = "I didn't catch that. Could you please provide more details?"

    final_response = UnifiedResponse(
        intent=intent,
        urgency=urgency,
        extracted_entities=state.get("entities", {}),
        action_taken=action_taken,
        response_message=response_msg
    )
    
    logger.info(f"Rules Engine Decision: {action_taken}")
    return {"response": final_response}


