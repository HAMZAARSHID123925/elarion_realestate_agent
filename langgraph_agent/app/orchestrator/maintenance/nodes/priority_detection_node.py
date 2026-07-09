from typing import Dict, Any

from app.orchestrator.maintenance.state import MaintenanceState

EMERGENCY_KEYWORDS = ["gas smell", "active flooding", "no heat", "smoke", "co alarm", "carbon monoxide", "fire"]


async def priority_detection_node(state: MaintenanceState) -> Dict[str, Any]:
    """Hardcoded keyword detection for emergencies."""
    messages = state.get("messages", [])

    # Concatenate all user messages to check for keywords
    full_text = " ".join([m.content.lower() for m in messages if hasattr(m, "content") and m.type == "human"])

    for kw in EMERGENCY_KEYWORDS:
        if kw in full_text:
            return {"urgency": "EMERGENCY"}

    # Keep existing urgency (fallback to LLM)
    return {}
