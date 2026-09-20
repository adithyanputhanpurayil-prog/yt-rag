"""Vector store backed by Pinecone (managed, free Starter tier).

Same interface as the Chroma/Qdrant versions (collection_exists /
index_chunks / query_chunks), so main.py doesn't change beyond the import.

Uses ONE Pinecone index for the whole app, with a separate NAMESPACE per
video. Namespaces are Pinecone's built-in way to partition vectors within
an index, so "is this video indexed" and "search only this video's chunks"
both fall out naturally instead of needing a manual metadata filter.
"""

import os
import uuid
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

INDEX_NAME = "yt-transcripts"
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536  # dimensionality of text-embedding-3-small

_pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
_openai = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"))


def _ensure_index() -> None:
    existing = [idx["name"] for idx in _pc.list_indexes()]
    if INDEX_NAME not in existing:
        _pc.create_index(
            name=INDEX_NAME,
            dimension=EMBED_DIM,
            metric="cosine",
            # us-east-1 is the region Pinecone's free Starter tier supports.
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )


_ensure_index()
_index = _pc.Index(INDEX_NAME)


def _embed(texts: list[str]) -> list[list[float]]:
    res = _openai.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in res.data]


def collection_exists(video_id: str) -> bool:
    """True if this video's namespace already has vectors in it."""
    stats = _index.describe_index_stats()
    ns = stats.namespaces.get(video_id)
    return bool(ns) and ns.vector_count > 0


def index_chunks(video_id: str, chunks: list[str]) -> int:
    vectors = _embed(chunks)
    items = [
        {"id": str(uuid.uuid4()), "values": vec, "metadata": {"text": chunk}}
        for chunk, vec in zip(chunks, vectors)
    ]
    _index.upsert(vectors=items, namespace=video_id)
    return len(items)


def query_chunks(video_id: str, question: str, k: int = 4) -> list[str]:
    q_vector = _embed([question])[0]
    result = _index.query(vector=q_vector, top_k=k, namespace=video_id, include_metadata=True)
    return [match["metadata"]["text"] for match in result["matches"]]
