"""
clarify_node -- design doc section 3 / 7.2.

Deterministic, no LLM call -- fast and cheap, matching the project's rule of
keeping simple decisions as plain Python. Asks exactly one targeted follow-up
question (design doc section 5.3: "ask one targeted follow-up before calling
MCP, avoid broad unfiltered calls" -- and section 3's UNCLEAR path: "single
follow-up question").

Multi-turn continuation: this node ends the turn with clarify_question as the
response. The graph is compiled with a checkpointer keyed by session_id
(design doc section 7.4), so the next turn re-enters with property_filters /
intent already accumulated in state.
"""
from app.orchestrator.faq.state import FAQState

FIELD_QUESTIONS = {
    "location": "Which city or area are you looking in?",
    "property_type": "What type of property -- apartment, house, condo, or studio?",
    "budget": "What's your budget range?",
}

UNCLEAR_QUESTION = "Could you tell me a bit more -- are you asking about a policy or looking for a property?"


def clarify_node(state: FAQState) -> dict:
    if state.get("intent") == "UNCLEAR":
        question = UNCLEAR_QUESTION
    else:
        missing = state.get("missing_property_fields") or []
        # Ask about the first missing field only -- "one targeted follow-up," not all at once.
        question = FIELD_QUESTIONS.get(missing[0], "Could you share a bit more detail?") if missing else UNCLEAR_QUESTION

    return {
        "clarify_question": question,
        "messages": [{"role": "assistant", "content": question}],
    }
