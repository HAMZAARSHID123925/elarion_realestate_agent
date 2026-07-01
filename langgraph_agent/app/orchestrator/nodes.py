import logging
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from app.orchestrator.state import OrchestratorState
from app.orchestrator.schemas import UnifiedResponse
from app.orchestrator.rate_limiter import groq_queue

logger = logging.getLogger(__name__)

# Initialize LLM
def get_llm():
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# --- Pydantic Schema for Unified Structured Output ---

class ClassificationResult(BaseModel):
    intent: Literal["maintenance", "leasing", "billing", "property_search", "general"] = Field(
        description="The primary intent of the user's message."
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
    Identifies the user from the database. 
    Fail-closed implementation: defaults to unknown/guest unless a strict match is found.
    """
    user_id = state["request"].user_id
    
    # TEMP MOCK: Replace this block with a real TENANCIES query once that table exists
    # mock_db_lookup would normally return None if not found.
    tenant = None
    if user_id == "tenant@example.com" or user_id == "+923001234567": # Only strict matches pass
        tenant = {"id": user_id, "role": "tenant", "property_id": "PROP_001"}
    
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
- intent: one of maintenance, leasing, property_search, billing, general
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
        # FAIL-SAFE: If LLM fails, assume it's a high-priority unknown issue
        return {
            "intent": "general",
            "urgency": "high",
            "entities": {}
        }

async def rules_engine_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Applies business rules to determine the final action based on state.
    """
    intent = state.get("intent", "general")
    urgency = state.get("urgency", "high")
    role = state.get("user_profile", {}).get("role", "guest")
    
    action_taken = "need_more_info"
    response_msg = "Your request has been received."
    
    # Business Rules
    if urgency == "high":
        action_taken = "human_escalation"
        response_msg = "This is an emergency. Escalating to a human manager immediately."
    elif intent == "maintenance":
        action_taken = "routed_to_maintenance_workflow"
        response_msg = "I have logged your maintenance request. The maintenance team will be notified."
    elif intent == "property_search":
        action_taken = "routed_to_property_search_workflow"
        response_msg = "Let me look up properties for you."
    elif intent == "leasing":
        action_taken = "routed_to_leasing_workflow"
        response_msg = "I will connect you with our leasing department."
    else:
        action_taken = "general_inquiry"
        response_msg = "Thank you for your message. An agent will review it shortly."
        
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
