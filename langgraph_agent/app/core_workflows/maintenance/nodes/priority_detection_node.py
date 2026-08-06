from typing import Dict, Any

from app.core_workflows.maintenance.state import MaintenanceState

# NOTE on label: this deterministic keyword safety net is the ONLY place that
# produces the "emergency" urgency label -- the LLM extraction in common.py
# is restricted to low/medium/high on purpose, so "emergency" always means
# this keyword net specifically fired. Label is lowercase to match the rest
# of the urgency vocabulary used everywhere else (low/medium/high) instead of
# the previous "EMERGENCY" (all caps), which is what let a genuinely urgent,
# AI-classified "high" ticket silently skip emergency-vendor routing in
# mcp_server.py's assign_vendor (it only ever checked for the exact string
# "EMERGENCY", which the AI classifier never outputs). graph.py's
# priority_router and mcp_server.py's assign_vendor were updated to match
# this same lowercase "emergency" label.
#
# English + Roman Urdu / Urdu emergency phrases -- tenants here message in
# both, so the backup keyword net needs to catch both, not just English.
EMERGENCY_KEYWORDS = [
    # English
    "gas smell", "gas leak", "gas leakage", "active flooding", "flooding", "flooded", "pipe burst", "burst pipe", "water pipe burst", "no heat", "smoke", "co alarm", "carbon monoxide", "fire",
    # Roman Urdu / Urdu (transliterated) equivalents
    "gas ki bu", "gas ki khushbu", "gas leak", "gas leakage", "aag lag", "aag lag gayi", "aag lagi",
    "dhuan", "dhuwan", "pani bhar gaya", "pani bharh gaya", "flooding ho gayi",
    "bijli ki chingari", "chingari", "short circuit", "karant", "aag ki",
]


async def priority_detection_node(state: MaintenanceState) -> Dict[str, Any]:
    """Hardcoded keyword detection for emergencies (English + Roman Urdu/Urdu backup net)."""
    messages = state.get("messages", [])

    # Concatenate all user messages to check for keywords
    full_text = " ".join([m.content.lower() for m in messages if hasattr(m, "content") and m.type == "human"])

    for kw in EMERGENCY_KEYWORDS:
        if kw in full_text:
            return {"urgency": "emergency"}

    # Keep existing urgency (fallback to LLM's low/medium/high classification)
    return {}
