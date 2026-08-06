"""
classify_intent_node -- design doc section 2.1 / 7.2.

The one and only LLM call that decides which of the 4 paths this turn takes.
Everything after this node is plain, deterministic Python (design doc section 7.3:
"keep the rules engine as plain conditionals, not LLM calls, for auditability
and latency") -- this node is the only place that thinks; the router that
follows it just reads the label.
"""
import logging
from app.core_workflows.faq.state import FAQState
from app.core_workflows.faq.schemas import IntentClassification
from app.core_workflows.faq.nodes.common import structured_call

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the intent classifier for a property management tenant support desk.
Classify the tenant's message into exactly one of: KNOWLEDGE, PROPERTY, MIXED, UNCLEAR.

KNOWLEDGE = policy/rules/process questions (pet policy, move-out process, deposit rules,
visitor rules, parking rules, lease terms).
PROPERTY = availability/budget/location/bedroom search ("do you have 2-bed apartments
under 100 lakhs in Lahore").
MIXED = both in the same message.
UNCLEAR = neither signal is clear -- needs a follow-up question.
"""


async def classify_intent_node(state: FAQState) -> dict:
    query = state["user_query"]

    result: IntentClassification = await structured_call(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        IntentClassification,
    )

    logger.info(f"[FAQ] classified intent={result.intent} for query={query!r}")

    return {
        "intent": result.intent,
        "messages": [{"role": "user", "content": query}],
    }
