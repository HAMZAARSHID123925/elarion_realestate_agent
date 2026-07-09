from typing import Dict, Any

from app.orchestrator.maintenance.state import MaintenanceState

SLOT_PROMPTS = {
    "tenant_identity": "Could you please provide your full name?",
    "property_unit": "Could you please confirm your property or unit number?",
    "issue_category": "What type of issue are you experiencing (e.g., plumbing, electrical, appliance)?",
    "issue_description": "Could you describe the issue in a bit more detail?",
    "urgency": "How urgent is this issue? Is there any active damage?",
    "permission_to_enter": "Do we have your permission to enter the unit to fix this if you are not home? (Yes/No)",
    "pets_present": "Are there any pets in the unit? (Yes/No)"
}


async def validation_node(state: MaintenanceState) -> Dict[str, Any]:
    """Loops back (or asks user) if mandatory slots missing."""
    missing = state.get("missing_slots", [])
    if missing:
        # Generate a hint of what to ask next
        next_question = SLOT_PROMPTS.get(missing[0], f"Please provide {missing[0]}.")
        return {"final_response": next_question}

    return {}
