import logging
from typing import Dict, Any, Literal, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from app.orchestrator.maintenance.state import MaintenanceState
# Try to use the rate limiter from orchestrator if available
try:
    from app.orchestrator.rate_limiter import groq_queue
    HAS_GROQ_QUEUE = True
except ImportError:
    HAS_GROQ_QUEUE = False

logger = logging.getLogger(__name__)

def get_llm():
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# In-memory fake dictionaries for Stage 1
FAKE_TENANT_DB = {
    "+923001234567": {"name": "Hamza Arshid", "unit": "Apt 4B"},
    "tenant@example.com": {"name": "John Doe", "unit": "House 12"}
}

MANDATORY_SLOTS = [
    "tenant_identity",
    "property_unit",
    "issue_category",
    "issue_description",
    "urgency",
    "permission_to_enter",
    "pets_present"
]

class MaintenanceExtraction(BaseModel):
    tenant_identity: str | None = Field(default=None, description="The name of the tenant. Null if not mentioned.")
    property_unit: str | None = Field(default=None, description="The property or unit number. Null if not mentioned.")
    issue_category: str | None = Field(default=None, description="The category of the maintenance issue (e.g., plumbing, electrical). Null if not mentioned.")
    issue_description: str | None = Field(default=None, description="Detailed description of the problem. Null if not mentioned.")
    urgency: Literal["low", "medium", "high"] | None = Field(default=None, description="The urgency of the request. Null if not mentioned.")
    permission_to_enter: Literal["yes", "no", "unconfirmed"] | None = Field(default=None, description="Whether the tenant grants permission to enter. If asked but not clearly answered, use 'unconfirmed'. Null if not mentioned.")
    pets_present: Literal["yes", "no", "unconfirmed"] | None = Field(default=None, description="Whether there are pets. If asked but not clearly answered, use 'unconfirmed'. Null if not mentioned.")

from app.orchestrator.maintenance.mcp_client import mcp_client
import json

async def receptionist_node(state: MaintenanceState) -> Dict[str, Any]:
    """Tenant lookup over MCP. Stores display identity + real DB IDs."""
    updates = {}
    
    # If already identified, skip
    if state.get("tenant_identity") and state.get("property_unit"):
        return updates
        
    user_id = state.get("user_id")
    if user_id:
        result_json = await mcp_client.call_tool("lookup_tenant", {"phone_or_email": user_id})
        if result_json:
            result = json.loads(result_json)
            if "error" not in result:
                updates["tenant_identity"] = result.get("name")         # display name for conversation
                updates["property_unit"]   = result.get("unit_id")      # unit label
                updates["db_tenant_id"]    = result.get("tenant_id")    # real DB FK
                updates["db_unit_id"]      = result.get("unit_id")      # real DB FK
                logger.info(f"Receptionist: Found tenant {updates['tenant_identity']} "
                            f"(id={updates['db_tenant_id']}) in {updates['property_unit']}")
            else:
                logger.info(f"Receptionist: Unknown tenant. {result.get('error')}")
    else:
        logger.info("Receptionist: No user_id provided.")
    
    return updates

async def issue_collection_node(state: MaintenanceState) -> Dict[str, Any]:
    """Wraps existing extraction logic with state merging."""
    llm = get_llm()
    messages = state.get("messages", [])
    
    if not messages:
        return {}
        
    # Assume the latest message is from the user
    latest_msg = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
    
    # Format the full history for the LLM
    history_str = "\n".join(
        f"{'User' if m.type == 'human' else 'Agent'}: {m.content}" 
        for m in messages if hasattr(m, "type")
    )
    
    # Prepare current slots to show LLM
    current_slots = {
        "tenant_identity": state.get("tenant_identity"),
        "property_unit": state.get("property_unit"),
        "issue_category": state.get("issue_category"),
        "issue_description": state.get("issue_description"),
        "urgency": state.get("urgency"),
        "permission_to_enter": state.get("permission_to_enter"),
        "pets_present": state.get("pets_present")
    }
    
    prompt = f"""You are an AI extracting maintenance request details.
Current Slots already collected:
{current_slots}

Latest user message:
"{latest_msg}"

Full Conversation History:
{history_str}

Your task: Extract ANY NEW information provided in the latest message.
- If a slot is already filled and the user hasn't corrected it, you can leave it null (or return the existing value).
- If the user explicitly corrects a slot, output the new value.
- If `permission_to_enter` or `pets_present` was asked but the user's response is vague or evasive, store as "unconfirmed". DO NOT guess.
"""
    
    try:
        if HAS_GROQ_QUEUE:
            result = await groq_queue.call(
                llm.with_structured_output(MaintenanceExtraction).ainvoke, 
                prompt
            )
        else:
            result = await llm.with_structured_output(MaintenanceExtraction).ainvoke(prompt)
             
        # Merge new extractions into state
        updates = {}
        for field in ["tenant_identity", "property_unit", "issue_category", "issue_description", "urgency", "permission_to_enter", "pets_present"]:
            new_val = getattr(result, field)
            # Update if new_val is not None
            if new_val is not None:
                updates[field] = new_val
                
        # Check missing mandatory slots
        missing = []
        for slot in MANDATORY_SLOTS:
            # Check state and updates
            val = updates.get(slot, state.get(slot))
            if not val:
                missing.append(slot)
                
        updates["missing_slots"] = missing
        return updates
        
    except Exception as e:
        logger.error(f"Extraction LLM failed: {e}")
        return {}

async def validation_node(state: MaintenanceState) -> Dict[str, Any]:
    """Loops back (or asks user) if mandatory slots missing."""
    missing = state.get("missing_slots", [])
    if missing:
        # Generate a hint of what to ask next
        slot_prompts = {
            "tenant_identity": "Could you please provide your full name?",
            "property_unit": "Could you please confirm your property or unit number?",
            "issue_category": "What type of issue are you experiencing (e.g., plumbing, electrical, appliance)?",
            "issue_description": "Could you describe the issue in a bit more detail?",
            "urgency": "How urgent is this issue? Is there any active damage?",
            "permission_to_enter": "Do we have your permission to enter the unit to fix this if you are not home? (Yes/No)",
            "pets_present": "Are there any pets in the unit? (Yes/No)"
        }
        next_question = slot_prompts.get(missing[0], f"Please provide {missing[0]}.")
        return {"final_response": next_question}
    
    return {}

async def priority_detection_node(state: MaintenanceState) -> Dict[str, Any]:
    """Hardcoded keyword detection for emergencies."""
    messages = state.get("messages", [])
    
    # Concatenate all user messages to check for keywords
    full_text = " ".join([m.content.lower() for m in messages if hasattr(m, "content") and m.type == "human"])
    
    keywords = ["gas smell", "active flooding", "no heat", "smoke", "co alarm", "carbon monoxide", "fire"]
    
    for kw in keywords:
        if kw in full_text:
            return {"urgency": "EMERGENCY"}
            
    # Keep existing urgency (fallback to LLM)
    return {}

async def escalation_node(state: MaintenanceState) -> Dict[str, Any]:
    """Produces escalation record + plain-language handoff."""
    record = {
        "tenant": state.get("tenant_identity"),
        "unit": state.get("property_unit"),
        "issue": state.get("issue_description"),
        "reason": "EMERGENCY priority detected"
    }
    logger.info("TODO: Live transfer integration needed here.")
    
    return {
        "escalation_record": record,
        "final_response": "This sounds like an emergency. I am escalating this to a live human manager immediately. Please stay on the line."
    }

async def request_builder_node(state: MaintenanceState) -> Dict[str, Any]:
    """Assembles validated slots into payload."""
    payload = {
        # Prefer resolved DB IDs; fall back to conversation-extracted values
        "tenant_id": state.get("db_tenant_id") or state.get("tenant_identity"),
        "unit_id": state.get("db_unit_id") or state.get("property_unit"),
        "category": state.get("issue_category"),
        "description": state.get("issue_description"),
        "urgency": state.get("urgency"),
        "permission_to_enter": state.get("permission_to_enter"),
        "pets_present": state.get("pets_present")
    }
    return {"ticket_payload": payload}

import uuid

async def ticket_creation_node(state: MaintenanceState) -> Dict[str, Any]:
    """Calls MCP server to create ticket."""
    payload = state.get("ticket_payload", {})
    
    # Generate client-side idempotency key
    idempotency_key = f"idem-{uuid.uuid4()}"
    
    # Map payload to MCP tool arguments
    args = {
        "tenant_id": payload.get("tenant_id") or "UNKNOWN",
        "unit_id": payload.get("unit_id") or "UNKNOWN",
        "category": payload.get("category") or "general",
        "description": payload.get("description") or "",
        "urgency": payload.get("urgency") or "low",
        "permission_to_enter": payload.get("permission_to_enter") or "unconfirmed",
        "pets_present": payload.get("pets_present") or "unconfirmed",
        "idempotency_key": idempotency_key
    }
    
    print(f"\n[TICKET CREATION] -> Calling MCP create_ticket with args: {args}")
    
    try:
        result_json = await mcp_client.call_tool("create_ticket", args)
        if result_json:
            result = json.loads(result_json)
            print(f"  [MCP RESPONSE] -> {result}")
            if result.get("status") in ["success", "duplicate"]:
                return {"ticket_creation_status": "success", "ticket_creation_error": None}
            else:
                error_msg = result.get("message") or result.get("error") or "Unknown error"
                print(f"  [MCP ERROR from Server] -> {error_msg}")
                return {"ticket_creation_status": "error", "ticket_creation_error": error_msg}
        else:
            return {"ticket_creation_status": "error", "ticket_creation_error": "Empty response"}
    except Exception as e:
        logger.error(f"  [MCP EXCEPTION] -> {e}")
        return {"ticket_creation_status": "error", "ticket_creation_error": str(e)}

async def response_generator_node(state: MaintenanceState) -> Dict[str, Any]:
    """Confirmation back to caller."""
    if state.get("ticket_creation_status") == "error":
        return {
            "final_response": "I'm having trouble saving this right now due to a system error, but a team member will follow up shortly regarding your request."
        }
    return {
        "final_response": "Thank you. Your maintenance request has been successfully created. Our team will be notified shortly."
    }
