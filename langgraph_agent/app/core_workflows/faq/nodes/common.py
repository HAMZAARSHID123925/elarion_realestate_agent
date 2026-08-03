"""
Shared clients for the FAQ subgraph's nodes: LLM, Gemini embeddings, Pinecone index.

All credentials are read from environment variables only -- nothing hardcoded.
Required env vars (add real values to langgraph_agent/.env):
    GOOGLE_API_KEY          -- Gemini embeddings (same provider used in Cubot)
    PINECONE_API_KEY        -- Pinecone vector DB
    PINECONE_INDEX_NAME     -- defaults to "elarion-faq" if not set
    PINECONE_NAMESPACE      -- defaults to "policy-docs" if not set

If these are missing, the FAQ knowledge path will raise a clear RuntimeError
at call time (not at import time), so the rest of the app / other departments
are unaffected until you actually hit the KNOWLEDGE or MIXED path.
"""
import os
import logging
from typing import Literal

from pydantic import BaseModel
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.65  # lower threshold as Gemini short text similarity is typically 0.6-0.7
TOP_K = 6                     # design doc section 4 -- retriever top-k (4-6)

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "elarion-faq")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "policy-docs")
# text-embedding-004 is deprecated -- gemini-embedding-001 is the current model.
# It defaults to 3072 dimensions; we request 768 explicitly (one of Google's
# three supported sizes) to keep the Pinecone index small and fast. This must
# stay in sync with EMBEDDING_DIMENSION in ingestion/config.py.
GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"
GEMINI_EMBEDDING_DIMENSION = 768


def get_llm():
    """Same convention as maintenance/nodes/common.py -- Groq, temperature 0."""
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


# Reuse the same rate limiter as the rest of the orchestrator, so FAQ's Groq
# calls share the concurrency cap instead of adding a second uncoordinated queue.
try:
    from app.orchestrator.rate_limiter import groq_queue
    HAS_GROQ_QUEUE = True
except ImportError:
    HAS_GROQ_QUEUE = False
    groq_queue = None


async def structured_call(prompt_messages, schema: type[BaseModel]):
    """
    Single shared helper: run a structured-output LLM call through the
    rate limiter if available, otherwise directly. Every node that needs
    structured output (classify_intent, groundedness check, slot extraction)
    goes through this one function.
    """
    llm = get_llm().with_structured_output(schema)

    async def _call():
        return await llm.ainvoke(prompt_messages)

    if HAS_GROQ_QUEUE and groq_queue is not None:
        return await groq_queue.call(_call)
    return await _call()


def get_embedding_client():
    """
    Gemini embedding client. Raises a clear error if GOOGLE_API_KEY isn't set yet,
    rather than failing silently or at import time.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to langgraph_agent/.env to enable "
            "the FAQ knowledge (RAG) path. Property search and general routing "
            "are unaffected."
        )
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=api_key,
        output_dimensionality=GEMINI_EMBEDDING_DIMENSION,
    )


def get_pinecone_index():
    """
    Pinecone index client. Raises a clear error if PINECONE_API_KEY isn't set yet.
    Does NOT create the index -- that happens once via ingestion/ingest.py.
    """
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "PINECONE_API_KEY is not set. Add it to langgraph_agent/.env to enable "
            "the FAQ knowledge (RAG) path. Property search and general routing "
            "are unaffected."
        )
    from pinecone import Pinecone
    pc = Pinecone(api_key=api_key)
    existing = [idx["name"] for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        raise RuntimeError(
            f"Pinecone index '{PINECONE_INDEX_NAME}' does not exist yet. "
            f"Run ingestion/ingest.py first to create it and load documents."
        )
    return pc.Index(PINECONE_INDEX_NAME)
