"""
Ingestion pipeline -- design doc section 4.

Loads a document (.txt today, .pdf once the client provides real policy PDFs),
chunks it with simple section-aware, overlapping word chunks, embeds each
chunk with Gemini, and upserts into Pinecone with citation metadata.

Usage (from langgraph_agent/):
    python -m app.orchestrator.faq.ingestion.ingest --file app/orchestrator/faq/knowledge_base/sample_pet_policy.txt

Requires PINECONE_API_KEY and GOOGLE_API_KEY set in langgraph_agent/.env.
Creates the Pinecone index on first run if it doesn't exist yet.
"""
import os
import re
import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from app.orchestrator.faq.ingestion.config import (
    CHUNK_SIZE_WORDS,
    CHUNK_OVERLAP_WORDS,
    EMBEDDING_DIMENSION,
    PINECONE_CLOUD,
    PINECONE_REGION,
)
from app.orchestrator.faq.nodes.common import PINECONE_INDEX_NAME, PINECONE_NAMESPACE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECTION_HEADER_PATTERN = re.compile(r"^\s*(#+\s*.+|[A-Z][A-Za-z0-9 /&-]{2,60}:?)\s*$")


def load_text(file_path: Path) -> str:
    """Loads .txt today. .pdf support is here and ready for when the client
    provides real policy PDFs -- no code changes needed at that point,
    just point --file at the .pdf."""
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError(
                "pypdf is not installed. Run: pip install pypdf --break-system-packages"
            )
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    raise ValueError(f"Unsupported file type: {suffix}. Use .txt or .pdf.")


def chunk_text(text: str, source: str) -> list[dict]:
    """
    Simple section-aware chunker: tracks the most recent header-looking line
    so each chunk carries a `section` for citation (design doc section 4),
    then splits into overlapping word windows within each section.

    This is a first pass, not the full semantic chunker from design doc
    section 4 -- good enough to validate the pipeline end to end with a
    .txt file now; swap in a smarter splitter later without touching the
    rest of the graph.
    """
    lines = text.splitlines()
    current_section = None
    section_buffer: list[str] = []
    sections: list[tuple[str | None, str]] = []

    for line in lines:
        if SECTION_HEADER_PATTERN.match(line.strip()) and len(line.strip()) < 80:
            if section_buffer:
                sections.append((current_section, " ".join(section_buffer)))
                section_buffer = []
            current_section = line.strip().strip("#: ")
        else:
            if line.strip():
                section_buffer.append(line.strip())

    if section_buffer:
        sections.append((current_section, " ".join(section_buffer)))

    if not sections:
        sections = [(None, text)]

    chunks = []
    for section_name, section_text in sections:
        words = section_text.split()
        if not words:
            continue
        start = 0
        while start < len(words):
            end = start + CHUNK_SIZE_WORDS
            chunk_words = words[start:end]
            chunks.append(
                {
                    "text": " ".join(chunk_words),
                    "source": source,
                    "section": section_name,
                }
            )
            if end >= len(words):
                break
            start = end - CHUNK_OVERLAP_WORDS

    return chunks


def ensure_index(pc):
    from pinecone import ServerlessSpec

    existing = [idx["name"] for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        logger.info(f"Creating Pinecone index '{PINECONE_INDEX_NAME}'...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
        )
    return pc.Index(PINECONE_INDEX_NAME)


def ingest_file(file_path: str):
    from pinecone import Pinecone
    from app.orchestrator.faq.nodes.common import get_embedding_client

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)

    pinecone_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_key:
        raise RuntimeError("PINECONE_API_KEY is not set in langgraph_agent/.env")

    text = load_text(path)
    chunks = chunk_text(text, source=path.name)
    logger.info(f"Loaded {path.name} -> {len(chunks)} chunks")

    embedder = get_embedding_client()
    pc = Pinecone(api_key=pinecone_key)
    index = ensure_index(pc)

    vectors = []
    for i, chunk in enumerate(chunks):
        vector = embedder.embed_query(chunk["text"], output_dimensionality=EMBEDDING_DIMENSION)
        vectors.append(
            {
                "id": f"{path.stem}-{i}",
                "values": vector,
                "metadata": {
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "section": chunk["section"] or "",
                },
            }
        )

    index.upsert(vectors=vectors, namespace=PINECONE_NAMESPACE)
    logger.info(f"Upserted {len(vectors)} vectors into '{PINECONE_INDEX_NAME}' (namespace='{PINECONE_NAMESPACE}')")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to a .txt or .pdf policy document")
    args = parser.parse_args()
    ingest_file(args.file)
