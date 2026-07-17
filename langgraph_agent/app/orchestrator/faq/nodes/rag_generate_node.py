"""
rag_generate_node -- design doc section 4 / 7.2.

Only reached when the confidence gate in rag_retrieve_node passed. Generates
the grounded answer, constrained strictly to the retrieved context, with a
citation per design doc section 4 ("Pet Policy, Sec. 3" style).
"""
import logging
from app.orchestrator.faq.state import FAQState
from app.orchestrator.faq.nodes.common import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You answer tenant policy questions using ONLY the excerpts provided below.
Do not use any outside knowledge. If the excerpts don't fully answer the question,
say so plainly rather than guessing.

After the answer, cite the source in parentheses, e.g. (Pet Policy, Sec. 3).
Keep the answer to 2-4 sentences.
"""


async def rag_generate_node(state: FAQState) -> dict:
    query = state["user_query"]
    chunks = state.get("rag_context", [])

    context_text = "\n\n".join(f"[{c['source']} - {c['section'] or 'n/a'}]: {c['text']}" for c in chunks)

    llm = get_llm()
    response = await llm.ainvoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Excerpts:\n{context_text}\n\nQuestion: {query}"},
        ]
    )

    answer = response.content

    return {
        "knowledge_answer": answer,
        "messages": [{"role": "assistant", "content": answer}],
    }
