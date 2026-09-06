import logging
from typing import Dict, Any

from app.core_workflows.maintenance.state import MaintenanceState
from app.core_workflows.maintenance.nodes.common import (
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
    active_question = missing_slots[0] if missing_slots else "None (collecting general info)"

    prompt = f"""You are an AI extracting maintenance request details from a tenant conversation.
Current Slots already collected:
{current_slots}

The agent's LAST question was asking the user for: '{active_question}'
The user's LATEST reply is their direct answer to that question.

Latest user message:
\"{latest_msg}\"

Full Conversation History:
{history_str}

Extraction rules:
- The user's latest reply is an ANSWER to the '{active_question}' slot. Extract it directly.
- A short reply like "yes", "no", "Unit 204", or a single phrase IS a valid answer for its slot.
- If a slot is already filled, keep it unless the user explicitly corrects it.
- For `permission_to_enter` and `pets_present`: "yes" -> "yes", "no" -> "no", vague -> "unconfirmed".
- For `urgency`: map casual language -> "high" (emergency/urgent), "medium" (broken/not working), "low" (cosmetic/minor).
- NEVER leave `{active_question}` as null if the user gave ANY non-empty reply about it."""

    json_prompt = f"""{prompt}

Output strictly a valid JSON object matching this schema:
{{
  "tenant_identity": "name or null",
  "property_unit": "unit number/name or null",
  "issue_category": "plumbing" | "electrical" | "hvac" | "general" | "security" | null,
  "issue_description": "short description or null",
  "urgency": "high" | "medium" | "low" | null,
  "permission_to_enter": "yes" | "no" | "unconfirmed" | null,
  "pets_present": "yes" | "no" | "unconfirmed" | null
}}
Output ONLY the JSON object."""

    try:
        from app.utils.helper import robust_json_parse
        fb_res = await llm.ainvoke(json_prompt)
        raw = fb_res.content if hasattr(fb_res, "content") else str(fb_res)
        data = robust_json_parse(raw, MANDATORY_SLOTS)

        updates = {}
        for field in ["tenant_identity", "property_unit", "issue_category", "issue_description", "urgency", "permission_to_enter", "pets_present"]:
            new_val = data.get(field)
            if new_val is not None:
                new_str = str(new_val).strip()
                if new_str.lower() in ["none", "null", "n/a", ""]:
                    new_val = None
                else:
                    new_val = new_str
            if new_val is not None:
                updates[field] = new_val

        # --- Deterministic slot extraction heuristics from latest user message ---
        latest_lower = (latest_msg or "").lower().strip()

        # 1. Issue Category
        if not updates.get("issue_category") and not state.get("issue_category"):
            if any(k in latest_lower for k in ["plumb", "pipe", "drain", "leak", "sink", "toilet", "tap", "faucet", "water", "sewer", "shower"]):
                updates["issue_category"] = "plumbing"
            elif any(k in latest_lower for k in ["electr", "light", "switch", "wiring", "socket", "power", "fuse", "breaker", "wifi", "wi-fi", "internet", "router", "cable", "modem", "network", "broadband"]):
                updates["issue_category"] = "electrical"
            elif any(k in latest_lower for k in ["ac", "air condition", "air conditioner", "hvac", "cooling", "heat", "heater", "radiator", "thermostat"]):
                updates["issue_category"] = "hvac"
            elif any(k in latest_lower for k in ["lock", "locks", "door", "window", "key", "keys", "security", "latch"]):
                updates["issue_category"] = "security"
            elif any(k in latest_lower for k in ["paint", "painting", "wall", "walls", "floor", "carpenter", "roof", "cabinet", "tiles", "pest"]):
                updates["issue_category"] = "general"
            elif active_question == "issue_category" and len(latest_lower) > 0:
                # User gave a direct answer to the category question
                updates["issue_category"] = "general"

        # 2. Permission to enter
        if not updates.get("permission_to_enter") and not state.get("permission_to_enter"):
            if active_question == "permission_to_enter" or any(k in latest_lower for k in ["permission", "enter", "access"]):
                # Negative check MUST come first so "no you cannot enter" evaluates to "no"
                if any(k in latest_lower for k in ["no", "never", "cannot", "can't", "cant", "not allowed", "don't", "dont", "refuse", "prohibited", "only when", "absence", "presence"]):
                    updates["permission_to_enter"] = "no"
                elif any(k in latest_lower for k in ["yes", "yeah", "yep", "sure", "ok", "okay", "fine", "allowed", "permitted", "granted", "anytime", "go ahead", "can enter", "you can enter", "free to enter"]):
                    updates["permission_to_enter"] = "yes"

        # 3. Pets present
        if not updates.get("pets_present") and not state.get("pets_present"):
            if active_question == "pets_present" or any(k in latest_lower for k in ["pet", "pets", "dog", "cat", "animal"]):
                # Negative check MUST come first so "no pets" evaluates to "no"
                if any(k in latest_lower for k in ["no", "none", "no pet", "no pets", "nah", "nope", "don't have", "dont have", "zero"]):
                    updates["pets_present"] = "no"
                elif any(k in latest_lower for k in ["yes", "dog", "cat", "have pet", "have pets", "have a dog", "have a cat", "puppy", "kitten"]):
                    updates["pets_present"] = "yes"

        # 4. Urgency heuristic
        if not updates.get("urgency") and not state.get("urgency"):
            if active_question == "urgency" or any(k in latest_lower for k in ["urgent", "urgency", "emergency", "priority"]):
                if any(k in latest_lower for k in ["not urgent", "not too much urgent", "not really", "low", "minor", "cosmetic", "routine", "no rush", "whenever", "next week", "coming week", "no hurry", "casual", "take time"]):
                    updates["urgency"] = "low"
                elif any(k in latest_lower for k in ["high", "urgent", "danger", "emergency", "burst", "leak", "immediately", "asap", "critical", "severe"]):
                    updates["urgency"] = "high"
                elif active_question == "urgency" and len(latest_lower) > 0:
                    updates["urgency"] = "medium"

        # 5. Issue description fallback
        if not updates.get("issue_description") and not state.get("issue_description"):
            if latest_lower and len(latest_lower) > 5:
                updates["issue_description"] = latest_msg[:200]

        # Check missing mandatory slots
        missing = []
        for slot in MANDATORY_SLOTS:
            val = updates.get(slot, state.get(slot))
            if not val or str(val).lower() in ["none", "null", ""]:
                missing.append(slot)

        updates["missing_slots"] = missing
        return updates

    except Exception as e:
        logger.error(f"Issue extraction failed: {e}")
        missing = []
        for slot in MANDATORY_SLOTS:
            if not state.get(slot):
                missing.append(slot)
        return {"missing_slots": missing if missing else MANDATORY_SLOTS}
