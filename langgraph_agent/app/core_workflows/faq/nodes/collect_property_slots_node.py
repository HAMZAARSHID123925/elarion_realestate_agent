"""
collect_property_slots_node -- design doc section 5.3 / 7.2.

Two separate jobs, kept distinct on purpose:
1. Slot EXTRACTION from this turn's message -- this is the one LLM/structured-output
   call in this node, same pattern as MaintenanceExtraction.
2. Slot COMPLETENESS check (deterministic Python) -- decides missing vs complete,
   which the graph's conditional edge (design doc section 7.3) uses to route to
   clarify vs call_property_mcp. This part is plain conditionals, not an LLM call,
   matching the project's existing rule for auditability and latency.
"""
import logging
from app.core_workflows.faq.state import FAQState
from app.core_workflows.faq.schemas import PropertySlotExtraction
from app.core_workflows.faq.nodes.common import structured_call

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["location", "property_type", "budget"]  # bedrooms is optional, per design doc section 5.1

SYSTEM_PROMPT = """Extract property search details from the tenant's message.
Only extract what is explicitly stated -- do not guess or infer missing values."""


async def collect_property_slots_node(state: FAQState) -> dict:
    query = state["user_query"]
    existing_filters = dict(state.get("property_filters") or {})

    extraction: PropertySlotExtraction = await structured_call(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        PropertySlotExtraction,
    )

    # Merge new slots over existing ones (design doc section 6: "user changes budget
    # mid-conversation" -> update session slot, keep the rest).
    new_values = extraction.model_dump(exclude_none=True)
    merged_filters = {**existing_filters, **new_values}

    missing = [f for f in REQUIRED_FIELDS if not merged_filters.get(f)]

    logger.info(f"[FAQ] property_filters={merged_filters} missing={missing}")

    return {
        "property_filters": merged_filters,
        "missing_property_fields": missing,
    }
