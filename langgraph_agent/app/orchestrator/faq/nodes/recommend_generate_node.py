"""
recommend_generate_node -- design doc section 5.3 / 7.2.

Ranking (closest budget fit, then listed order) and a hard cap at top 3-5,
per design doc section 5.3 -- "never the full result set; summarize remaining count."
Handles the zero-match case with a nearest-alternative message instead of a
dead end (design doc section 6).
"""
import logging
from app.orchestrator.faq.state import FAQState
from app.orchestrator.faq.nodes.common import get_llm

logger = logging.getLogger(__name__)

MAX_RECOMMENDATIONS = 5

SYSTEM_PROMPT = """Write a short, friendly summary (3-5 sentences) recommending these
properties to a tenant, based on their search. Mention price, bedrooms/type, and
location for each. If the total match count is higher than the number listed,
mention that more are available and offer to narrow the search further."""


def _rank_and_cap(properties: list, target_budget: float | None) -> list:
    if target_budget is not None:
        properties = sorted(properties, key=lambda p: abs((p.get("price_lakhs") or p.get("price", 0)) - target_budget))
    return properties[:MAX_RECOMMENDATIONS]


async def recommend_generate_node(state: FAQState) -> dict:
    mcp_results = state.get("mcp_results") or {}
    filters = state.get("property_filters", {})

    if mcp_results.get("status") != "success" or not mcp_results.get("properties"):
        # Zero matches -- design doc section 6, offer nearest alternative rather than a dead end.
        text = (
            f"I couldn't find any {filters.get('property_type', 'properties')} in "
            f"{filters.get('location', 'that area')} within your budget. "
            f"Want me to check a nearby area or a slightly higher budget?"
        )
        return {"recommendation_text": text}

    properties = mcp_results["properties"]
    total_count = mcp_results.get("count", len(properties))

    try:
        target_budget = float(filters.get("budget", "").split()[0]) if filters.get("budget") else None
    except (ValueError, IndexError):
        target_budget = None

    top_matches = _rank_and_cap(properties, target_budget)

    llm = get_llm()
    response = await llm.ainvoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Total matches: {total_count}. Showing top {len(top_matches)}:\n{top_matches}",
            },
        ]
    )

    return {"recommendation_text": response.content}
