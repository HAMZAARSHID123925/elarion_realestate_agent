"""
rag_retrieve_node -- design doc section 4 / 7.2.

Embeds the query with Gemini, queries Pinecone (hybrid-ready, metadata filterable),
and computes the confidence gate: similarity threshold + an LLM self-check
("is this fully supported?"). This node sets confidence_score, which the graph's
conditional edge (design doc section 7.3) uses to decide escalate vs rag_generate.

Never touches the property/MCP data source -- design doc section 1: policy answers
never come from MCP, property data never comes from RAG.
"""
import logging
from app.core_workflows.faq.state import FAQState, RetrievedChunk
from app.core_workflows.faq.schemas import GroundednessCheck
from app.core_workflows.faq.nodes.common import (
    get_embedding_client,
    get_pinecone_index,
    structured_call,
    CONFIDENCE_THRESHOLD,
    TOP_K,
    PINECONE_NAMESPACE,
    GEMINI_EMBEDDING_DIMENSION,
)

logger = logging.getLogger(__name__)

GROUNDEDNESS_PROMPT = """You are checking whether the retrieved policy excerpts below
fully support answering the tenant's question. Do not use outside knowledge.

Question: {query}

Retrieved excerpts:
{context}
"""


async def rag_retrieve_node(state: FAQState) -> dict:
    query = state["user_query"]

    embedder = get_embedding_client()
    index = get_pinecone_index()

    query_vector = await embedder.aembed_query(query, output_dimensionality=GEMINI_EMBEDDING_DIMENSION)

    results = index.query(
        vector=query_vector,
        top_k=TOP_K,
        namespace=PINECONE_NAMESPACE,
        include_metadata=True,
    )

    chunks: list[RetrievedChunk] = []
    for match in results.get("matches", []):
        meta = match.get("metadata", {})
        chunks.append(
            RetrievedChunk(
                text=meta.get("text", ""),
                source=meta.get("source", "unknown"),
                section=meta.get("section"),
                score=match.get("score", 0.0),
            )
        )

    top_score = chunks[0]["score"] if chunks else 0.0

    if not chunks or top_score < CONFIDENCE_THRESHOLD:
        # Below similarity threshold -- skip the LLM self-check, escalate directly.
        # (design doc section 6, "Answer not in knowledge base")
        return {
            "rag_context": chunks,
            "confidence_score": top_score,
            "escalate": True,
            "escalation_reason": "No sufficiently relevant policy content found.",
        }

    context_text = "\n\n".join(f"[{c['source']} - {c['section'] or 'n/a'}]: {c['text']}" for c in chunks)

    groundedness: GroundednessCheck = await structured_call(
        [{"role": "user", "content": GROUNDEDNESS_PROMPT.format(query=query, context=context_text)}],
        GroundednessCheck,
    )

    if groundedness.is_supported == "no" or groundedness.confidence == "low":
        return {
            "rag_context": chunks,
            "confidence_score": top_score,
            "escalate": True,
            "escalation_reason": groundedness.reason,
        }

    return {
        "rag_context": chunks,
        "confidence_score": top_score,
        "escalate": False,
    }
