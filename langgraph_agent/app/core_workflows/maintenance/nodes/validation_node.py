import logging
from typing import Dict, Any

from app.core_workflows.maintenance.state import MaintenanceState

logger = logging.getLogger(__name__)

SLOT_PROMPTS = {
    "tenant_identity": "Could you please provide your full name?",
    "property_unit": "Could you please confirm your property or unit number?",
    "issue_category": "What type of issue are you experiencing (e.g., plumbing, electrical, HVAC, appliance)?",
    "issue_description": "Could you describe the issue in a bit more detail?",
    "urgency": "How urgent is this? Is there any active damage or safety concern? (high / medium / low)",
    "permission_to_enter": "Do we have your permission to enter the unit to fix this if you're not home? (Yes / No)",
    "pets_present": "Are there any pets in the unit we should know about? (Yes / No)"
}


async def validation_node(state: MaintenanceState) -> Dict[str, Any]:
    """Checks mandatory slots and asks for the first missing one.

    Anti-double-question guard: if the agent just asked for a slot and the
    user replied with ANY non-trivially-short answer but the LLM still didn't
    extract it, we accept the latest message as the answer for that slot to
    avoid an infinite ask loop.
    """
    missing = state.get("missing_slots", [])
    if not missing:
        return {}

    messages = state.get("messages", [])
    latest_human_msg = ""
    for m in reversed(messages):
        if hasattr(m, "type") and m.type == "human":
            latest_human_msg = (m.content or "").strip()
            break

    next_slot = missing[0]
    last_asked = state.get("last_asked_slot")

    # Anti-loop guard:
    # Trigger ONLY if this slot was ALREADY asked on the previous turn and the user replied,
    # but extraction still left it missing. Never ask the exact same question twice!
    is_repeated_question = (last_asked == next_slot)

    if is_repeated_question and latest_human_msg and len(latest_human_msg) >= 1:
        logger.info(
            f"validation_node: Anti-loop guard triggered for slot '{next_slot}'. "
            f"Auto-accepting answer: {latest_human_msg!r}"
        )
        text_lower = latest_human_msg.lower()
        if next_slot == "permission_to_enter":
            if any(w in text_lower for w in ["no", "never", "cannot", "can't", "cant", "not allowed", "don't", "dont", "refuse", "prohibited", "only when", "absence"]):
                accepted_val = "no"
            elif any(w in text_lower for w in ["yes", "sure", "ok", "fine", "allowed", "granted", "yep", "yeah", "can enter"]):
                accepted_val = "yes"
            else:
                accepted_val = "unconfirmed"
        elif next_slot == "pets_present":
            if any(w in text_lower for w in ["no", "none", "no pet", "no pets", "zero", "don't have", "dont have"]):
                accepted_val = "no"
            elif any(w in text_lower for w in ["yes", "dog", "cat", "have", "puppy"]):
                accepted_val = "yes"
            else:
                accepted_val = "no"
        elif next_slot == "issue_category":
            if any(w in text_lower for w in ["plumb", "pipe", "leak", "sink", "toilet", "water"]):
                accepted_val = "plumbing"
            elif any(w in text_lower for w in ["electr", "light", "switch", "wiring", "socket"]):
                accepted_val = "electrical"
            elif any(w in text_lower for w in ["ac", "air condition", "heat", "hvac"]):
                accepted_val = "hvac"
            elif any(w in text_lower for w in ["lock", "door", "window", "key"]):
                accepted_val = "security"
            else:
                accepted_val = "general"
        elif next_slot == "urgency":
            if any(w in text_lower for w in ["high", "urgent", "danger", "emergency", "burst", "leak"]):
                accepted_val = "high"
            elif any(w in text_lower for w in ["low", "minor", "cosmetic"]):
                accepted_val = "low"
            else:
                accepted_val = "medium"
        else:
            accepted_val = latest_human_msg[:200]

        remaining_missing = [s for s in missing if s != next_slot]
        next_prompt_slot = remaining_missing[0] if remaining_missing else None

        response_dict = {
            next_slot: accepted_val,
            "missing_slots": remaining_missing,
            "last_asked_slot": next_prompt_slot,
        }
        if next_prompt_slot:
            response_dict["final_response"] = SLOT_PROMPTS.get(next_prompt_slot, f"Please provide {next_prompt_slot}.")
        return response_dict

    # Normal path: ask the user for the first missing slot
    next_question = SLOT_PROMPTS.get(next_slot, f"Please provide {next_slot}.")
    logger.info(f"validation_node: Asking for missing slot '{next_slot}'")
    return {
        "final_response": next_question,
        "last_asked_slot": next_slot
    }
