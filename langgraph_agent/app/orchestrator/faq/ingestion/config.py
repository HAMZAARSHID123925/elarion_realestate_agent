"""Ingestion constants -- design doc section 4."""

CHUNK_SIZE_WORDS = 400      # roughly maps to the 300-500 token target
CHUNK_OVERLAP_WORDS = 60    # ~15% overlap
EMBEDDING_DIMENSION = 768   # Gemini text-embedding-004 output size
PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"
