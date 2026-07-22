import logging
from typing import Dict, Any

from app.orchestrator.maintenance.state import MaintenanceState
from app.orchestrator.maintenance.nodes.common import (
    get_llm,
    HAS_GROQ_QUEUE,
    groq_queue,
    MaintenanceExtraction,
    MANDATORY_SLOTS,
)

logger = logging.getLogger(__name__)


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

    missing_slots = state.get("missing_slots", [])
    active_question = missing_slots[0] if missing_slots else "None (just collecting general info)"

    prompt = f"""You are an AI extracting maintenance request details.
Current Slots already collected:
{current_slots}

Currently asking the user for: '{active_question}'

Latest user message:
"{latest_msg}"

Full Conversation History:
{history_str}

Your task: Extract ANY NEW information provided in the latest message.
- If the user provides a short answer like "Yes" or "No", use the 'Currently asking the user for' field to know which slot they are answering.
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
