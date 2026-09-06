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
# Model selection (2026-08-23 — confirmed working with structured output on this Groq key):
#
#  PRIMARY  → qwen/qwen3.6-27b      : Groq-native, tool-calling capable, generous rate limits ✅
#  FALLBACK → openai/gpt-oss-120b   : Most capable, use if Qwen hits limits
#
# ❌ groq/compound / groq/compound-mini do NOT support tool calling (needed for structured output)
# ❌ llama-3.3-70b-versatile / llama-3.1-70b-versatile — deprecated on this account
PRIMARY_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "openai/gpt-oss-20b"

def get_llm():
    return ChatGroq(model=PRIMARY_MODEL, temperature=0, max_tokens=600)

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
    # 1. Thread persistence: retain previously verified tenant identity on this conversation thread
    prev_profile = state.get("user_profile")
    if prev_profile and prev_profile.get("status") == "known":
        logger.info(f"Identified User: Retaining verified tenant ({prev_profile.get('user_id')}) from thread state")
        return {"user_profile": prev_profile}

    user_id = state["request"].user_id

    tenant = None
    try:
        result_json = await mcp_client.call_tool("lookup_tenant", {"phone_or_email": user_id})
        if isinstance(result_json, dict):
            result = result_json
        elif isinstance(result_json, str) and result_json.strip():
            result = json.loads(result_json)
        else:
            result = {}
            
        if result and "error" not in result and result.get("tenant_id"):
            tenant = {
                "id": result.get("tenant_id"),
                "role": "tenant",
                "property_id": result.get("property_id"),
                "name": result.get("name"),
                "unit_id": result.get("unit_id"),
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
            "property_id": tenant["property_id"],
            "name": tenant.get("name"),
            "unit_id": tenant.get("unit_id"),
        }
        logger.info(f"Identified User: Registered {tenant['role']} ({tenant['id']})")
    
    return {"user_profile": profile}

async def classify_and_extract_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Consolidated node that classifies intent, assesses urgency, and extracts entities
    in a SINGLE fast LLM call (<500ms) with robust JSON parsing and thinking-tag cleanup.

    Post-LLM safety rule: urgency='high' is ONLY allowed when genuine life-safety
    keywords are present. For everything else (broken locks, broken AC, etc.) the
    maintenance workflow's own priority_detection_node handles escalation via its
    hardcoded keyword net (English + Roman Urdu). This prevents the LLM from
    over-classifying normal maintenance into emergencies and bypassing ticket creation.
    """
    llm = get_llm()
    request = state["request"]

    # True life-safety keywords -- ONLY these justify urgency='high' at Layer 2.
    # Everything else should be medium/low and handled by the maintenance subgraph.
    LIFE_SAFETY_KEYWORDS = [
        "gas smell", "gas leak", "gas leakage", "active flooding", "flooding", "flooded",
        "pipe burst", "burst pipe", "no heat", "smoke", "carbon monoxide", "co alarm",
        "fire", "aag", "dhuan", "dhuwan", "pani bhar", "short circuit", "karant",
    ]

    json_prompt = f"""You are a property management triage classifier. Analyze this tenant message:
"{request.raw_text}"

Return ONLY a valid JSON object with exact structure:
{{
  "intent": "maintenance" | "leasing" | "billing" | "faq" | "general",
  "urgency": "high" | "medium" | "low",
  "entities": {{"key": "value"}}
}}

Intent Rules:
- "maintenance": repairs, leaks, broken items, locks, AC, plumbing, paint, damage, electrical, appliances, internet/wifi, router, cable, anything not working or malfunctioning.
- "faq": questions about rules, hours, parking, policies, deposits, building info.
- "leasing": finding properties, rent renewals, lease terms, availability.
- "billing": payments, receipts, balances, late fees.
- "general": ONLY simple greetings with NO issue or request (e.g. "hi", "hello", "good morning"), introducing oneself with name or unit number, "thank you", or unrelated chit-chat.

Entity Extraction Rules:
- Extract any mentioned user name (as "name") and unit or apartment number (as "unit") into "entities".
- Extract any physical issues, appliances, or rooms into "entities".

CRITICAL: If the tenant reports that ANYTHING is "not working", "broken", "issue", "problem", or malfunctioning (including wifi, internet, cable, appliances, lights, water, locks, doors), it MUST be classified as "maintenance", NEVER "general"!

Urgency Rules (be conservative -- default to medium for most issues):
- "high": ONLY for active danger: gas smell/leak, flooding, fire, smoke, carbon monoxide, burst pipe.
- "medium": broken locks, broken AC/heating, door issues, wifi/internet down, non-functional appliances, broken windows.
- "low": paint, minor cosmetic, routine questions, slow drains, minor repairs, light bulbs.

IMPORTANT: A broken lock or wifi issue is NOT an emergency -- it is medium or low urgency.
"""
    try:
        from app.utils.helper import robust_json_parse
        fb_res = await llm.ainvoke(json_prompt)
        raw = fb_res.content if hasattr(fb_res, "content") else str(fb_res)
        data = robust_json_parse(raw, ["intent", "urgency", "entities"])

        intent = data.get("intent", "general").lower()
        if intent not in ["maintenance", "leasing", "billing", "faq", "general"]:
            intent = "general"

        # Deterministic keyword safety net for maintenance:
        # If LLM classified as "general" (often because the message began with "Hi/Hello"),
        # but the message clearly contains physical maintenance / repair keywords or reports an issue, override to "maintenance".
        MAINTENANCE_KEYWORDS = [
            "lock", "locks", "door", "doors", "paint", "painting", "wall", "walls",
            "leak", "leaks", "leaking", "plumbing", "pipe", "pipes", "burst",
            "drain", "sink", "toilet", "tap", "faucet", "shower", "water",
            "ac", "air condition", "air conditioner", "hvac", "cooling", "heating", "heater",
            "broken", "fix", "repair", "repairs", "damage", "damaged", "renovate", "renovation",
            "electric", "electrical", "switch", "socket", "power", "fuse",
            "appliance", "stove", "fridge", "refrigerator", "oven", "dishwasher",
            "window", "windows", "glass", "roof", "ceiling", "floor", "flooring",
            "pest", "cockroach", "termite", "bugs", "infestation",
            "wifi", "wi-fi", "internet", "router", "cable", "modem", "network", "broadband",
            "not working", "not working properly", "not work", "doesn't work", "does not work", "stopped working",
            "problem", "problems", "issue", "issues", "fault", "faulty", "trouble", "malfunction",
            "bulb", "light", "lights", "fan", "geyser", "elevator", "lift",
            "khrab", "kharab", "toota", "tot gaya", "paani", "bijli", "marammat", "masla"
        ]
        raw_lower = (request.raw_text or "").lower()
        if intent == "general" and any(kw in raw_lower for kw in MAINTENANCE_KEYWORDS):
            logger.info(f"classify_and_extract_node: Overriding intent from 'general' -> 'maintenance' based on keyword match in: {request.raw_text[:60]!r}")
            intent = "maintenance"

        urgency = data.get("urgency", "low").lower()
        if urgency not in ["high", "medium", "low"]:
            urgency = "low"

        # Post-LLM safety downgrade: only allow high urgency if a genuine
        # life-safety keyword is present in the raw message.
        if urgency == "high":
            has_life_safety = any(kw in raw_lower for kw in LIFE_SAFETY_KEYWORDS)
            if not has_life_safety:
                logger.info(f"classify_and_extract_node: Downgrading urgency high->medium (no life-safety keywords in: {request.raw_text[:60]!r})")
                urgency = "medium"

        entities = data.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}

        # ── Secondary Identification for Unregistered / Guest Users ─────────
        profile_update = None
        current_profile = state.get("user_profile") or {}
        if current_profile.get("status") != "known":
            name_cand = entities.get("name") or entities.get("tenant_name")
            unit_cand = entities.get("unit") or entities.get("unit_id")

            # Fallback regex extraction if LLM missed them
            import re
            raw_text = request.raw_text or ""
            if not name_cand:
                name_m = re.search(r'(?:my\s+name\s+is|i\s+am|i\'m|name\s*[:=]|may\s+name\s+is)\s+([A-Za-z]+(?:\s+[A-Za-z]+)+)', raw_text, re.IGNORECASE)
                if name_m:
                    name_cand = name_m.group(1).strip()
            if not unit_cand:
                unit_m = re.search(r'\b(?:unit|apt|apartment|flat|house|u)[\s.\-#]+(\w+)\b', raw_text, re.IGNORECASE)
                if unit_m:
                    unit_cand = unit_m.group(1).strip()

            resolved = None
            if name_cand:
                try:
                    res_json = await mcp_client.call_tool("lookup_tenant_by_name", {"name": name_cand})
                    if res_json:
                        res = json.loads(res_json) if isinstance(res_json, str) else res_json
                        if res and "error" not in res and res.get("tenant_id"):
                            resolved = res
                except Exception as e:
                    logger.warning(f"classify_and_extract_node: name lookup failed: {e}")

            if not resolved and unit_cand:
                try:
                    res_json = await mcp_client.call_tool("lookup_tenant_by_unit", {"unit_id": unit_cand})
                    if res_json:
                        res = json.loads(res_json) if isinstance(res_json, str) else res_json
                        if res and "error" not in res and res.get("tenant_id"):
                            resolved = res
                except Exception as e:
                    logger.warning(f"classify_and_extract_node: unit lookup failed: {e}")

            if resolved:
                profile_update = {
                    "status": "known",
                    "role": "tenant",
                    "user_id": resolved.get("tenant_id"),
                    "property_id": resolved.get("property_id"),
                    "name": resolved.get("name"),
                    "unit_id": resolved.get("unit_id"),
                }
                logger.info(f"classify_and_extract_node: Resolved unregistered user via self-id -> {resolved.get('name')} ({resolved.get('tenant_id')}) in unit {resolved.get('unit_id')}")

        logger.info(f"Classified: {intent} | Urgency: {urgency}")
        result_payload = {
            "intent": intent,
            "urgency": urgency,
            "entities": entities,
            "error": None
        }
        if profile_update:
            result_payload["user_profile"] = profile_update
        return result_payload

    except Exception as e:
        logger.warning(f"Classification JSON parsing failed: {e}")
        raw_lower = (request.raw_text or "").lower()
        intent = "general"
        if any(w in raw_lower for w in ["leak", "broken", "repair", "door", "lock", "paint", "ac", "cool", "heat", "plumb", "water", "window"]):
            intent = "maintenance"
        elif any(w in raw_lower for w in ["policy", "rule", "hours", "pet", "parking", "deposit"]):
            intent = "faq"
        elif any(w in raw_lower for w in ["rent", "renew", "lease", "rate"]):
            intent = "leasing"
        return {
            "intent": intent,
            "urgency": "medium",
            "entities": {},
            "error": None
        }

async def rules_engine_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Applies business rules to determine the final action based on intent and urgency.
    Routes maintenance, FAQ, and rent renewal directly to their respective Layer 3 subgraphs.

    KEY DESIGN RULE: Maintenance ALWAYS routes to the maintenance workflow, regardless
    of urgency. The urgency field is passed through so the maintenance subgraph's own
    priority_detection_node can apply its hardcoded emergency keyword net and escalation
    logic. This ensures:
      - Tickets are ALWAYS created and saved to the database
      - The UI is ALWAYS updated
      - True emergencies (gas/fire/flood) are handled by escalation_node inside the subgraph
      - The old urgency=high bypass that skipped ticket creation is removed
    """
    intent = state.get("intent", "general")
    urgency = state.get("urgency", "medium")
    classification_failed = state.get("error") == "classification_failed"

    action_taken = "need_more_info"
    response_msg = "Your request has been received."

    if classification_failed:
        action_taken = "needs_human_review"
        response_msg = "I had a little trouble understanding that. Let me connect you with a team member."
    elif intent == "maintenance":
        # ALWAYS route maintenance to the maintenance workflow -- urgency is irrelevant here.
        action_taken = "routed_to_maintenance_workflow"
        response_msg = "I have logged your maintenance request. The maintenance team will be notified."
    elif intent == "faq" or intent == "billing":
        action_taken = "routed_to_faq_workflow"
        response_msg = "Let me find that information for you."
    elif intent in ("rent_renewal", "lease_renewal"):
        action_taken = "routed_to_rent_renewal_workflow"
        response_msg = "I will connect you with our rent renewal department."
    elif intent == "leasing":
        action_taken = "routed_to_faq_workflow"
        response_msg = "Let me look into that for you."
    else:
        # General inquiry -- check if user is identified or unknown
        user_profile = state.get("user_profile") or {}
        if user_profile.get("status") == "unknown":
            # Unknown user -- route to fallback which will ask them to self-identify
            action_taken = "needs_human_review"
            response_msg = "unknown_user_self_id"  # fallback_node will override this
        else:
            name = user_profile.get("name") or "there"
            unit = user_profile.get("unit_id") or ""
            unit_str = f" for unit {unit}" if unit else ""
            action_taken = "general_inquiry"
            response_msg = f"Hello {name}! I have verified your details{unit_str}. How can I assist you today with a maintenance request, rent inquiry, or lease question?"

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


