import os
import re
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.transcript import fetch_transcript, TranscriptUnavailable
from app.chunking import chunk_transcript
from app.vectorstore_pinecone import collection_exists, index_chunks, query_chunks
from app.llm import generate_answer

app = FastAPI(title="YouTube RAG API")

allowed = os.getenv("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allowed == "*" else allowed.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

_VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


class IngestRequest(BaseModel):
    video_id: str


class IngestResponse(BaseModel):
    video_id: str
    chunks_indexed: int
    already_indexed: bool


class QueryRequest(BaseModel):
    video_id: str
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


def _validate_video_id(video_id: str) -> str:
    if not _VIDEO_ID_RE.match(video_id):
        raise HTTPException(400, "Invalid YouTube video id")
    return video_id


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    video_id = _validate_video_id(req.video_id)

    # Avoid re-embedding a video that's already indexed -- this is the
    # single biggest cost/latency win for a tool people reuse on the same
    # videos.
    if collection_exists(video_id):
        return IngestResponse(video_id=video_id, chunks_indexed=0, already_indexed=True)

    try:
        transcript = fetch_transcript(video_id)
    except TranscriptUnavailable as e:
        raise HTTPException(422, f"No transcript available for this video: {e}")

    if not transcript.strip():
        raise HTTPException(422, "Transcript was empty")

    chunks = chunk_transcript(transcript)
    n = index_chunks(video_id, chunks)
    return IngestResponse(video_id=video_id, chunks_indexed=n, already_indexed=False)


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    video_id = _validate_video_id(req.video_id)
    if not collection_exists(video_id):
        raise HTTPException(404, "Video not indexed yet -- call /ingest first")

    chunks = query_chunks(video_id, req.question)
    answer = generate_answer(req.question, chunks)
    return QueryResponse(answer=answer, sources=chunks)
