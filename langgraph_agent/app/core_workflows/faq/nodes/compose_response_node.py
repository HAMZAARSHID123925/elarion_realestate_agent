"""
compose_response_node -- design doc section 3 / 7.2.

The single merge point every path flows through before returning to the
orchestrator (design doc section 6: "Multiple questions in one message ->
decompose, answer each, combine into one response" -- this node is where
that combining happens for MIXED, and where escalation / clarify messages
get finalized for the other paths).
"""
from app.core_workflows.faq.state import FAQState

ESCALATION_TEMPLATE = "I don't have reliable information on that. I'm escalating this to our team, and someone will follow up shortly."


def compose_response_node(state: FAQState) -> dict:
    parts = []

    if state.get("escalate"):
        parts.append(ESCALATION_TEMPLATE)
    elif state.get("knowledge_answer"):
        parts.append(state["knowledge_answer"])

    if state.get("recommendation_text"):
        parts.append(state["recommendation_text"])

    if not parts and state.get("clarify_question"):
        parts.append(state["clarify_question"])

    final_response = "\n\n".join(parts) if parts else "Sorry, I wasn't able to process that -- could you rephrase?"

    return {
        "final_response": final_response,
        "messages": [{"role": "assistant", "content": final_response}],
    }
