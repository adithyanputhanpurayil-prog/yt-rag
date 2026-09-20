# yt-rag
# YouTube Video Q&A — RAG app + Chrome extension

A minimal, production-shaped starting point. Backend does transcript → chunks
→ embeddings → vector store → retrieval → LLM answer. The extension is a thin
client: it detects the video you're on and talks to the backend over HTTP.

## Run it locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
uvicorn app.main:app --reload
```

Then in Chrome: `chrome://extensions` → enable Developer mode → **Load
unpacked** → select the `extension/` folder. Open any YouTube video, click
the extension icon, hit **Load transcript**, then ask a question.

## How the pieces fit

1. **Transcript** (`app/transcript.py`) — `youtube-transcript-api` pulls
   captions (manual or auto-generated) directly, no scraping or API key
   needed for this step.
2. **Chunking** (`app/chunking.py`) — `RecursiveCharacterTextSplitter`
   (800 chars, 150 overlap). This splitter respects sentence/paragraph
   boundaries before falling back to hard cuts, which keeps chunks
   semantically coherent — important since transcript text has no natural
   paragraph breaks.
3. **Embeddings + store** (`app/vectorstore_pinecone.py`) — OpenAI
   `text-embedding-3-small` (cheap, strong quality/cost ratio), stored in
   Pinecone with one **namespace** per video id, so retrieval is always
   scoped to the video being asked about.
4. **Retrieval + generation** (`app/main.py`, `app/llm.py`) — top-k (4)
   chunks by cosine similarity are stuffed into a prompt for `gpt-4o-mini`,
   instructed to answer only from the given excerpts.
5. **Extension** — popup reads the active tab's URL, extracts the video id,
   calls `/ingest` once per video, then `/query` per question.

## Why these choices

- **Chunk size 800/150** — big enough to carry a full thought from spoken
  transcript, small enough that retrieval stays precise and the LLM context
  stays cheap. For long lecture-style videos, consider 1000–1200 with the
  same ~15–20% overlap.
- **Skip re-ingesting** — `/ingest` checks if a video's namespace already
  has vectors before re-embedding. This is the single biggest cost/latency
  saving for a tool people reuse on popular videos.
- **Pinecone, one namespace per video** — a managed store means no local
  files to manage or lose, and a namespace per video keeps retrieval scoped
  to the video being asked about, avoids cross-video contamination, and
  means you can delete a single video's data cheaply.

## Setting up Pinecone

1. Create a free account at app.pinecone.io, grab an API key from the
   dashboard (no index setup needed -- the app creates its index
   automatically the first time it runs).
2. Add `PINECONE_API_KEY` to `.env` (see `.env.example`).

## Deploying the backend

1. **Containerize** — the included `Dockerfile` builds the API image. The
   container is fully stateless (all vector data lives in Pinecone), so it's
   safe to restart or redeploy anytime without losing anything:
   ```bash
   docker build -t yt-rag-backend ./backend
   docker run -p 8000:8000 --env-file backend/.env yt-rag-backend
   ```
2. **Host it** — any container platform works (Render, Fly.io, Railway,
   AWS ECS/Fargate, Google Cloud Run). Cloud Run / Fly.io are good defaults:
   cheap, autoscaling, HTTPS out of the box.
3. **Lock down CORS** — once deployed, set `ALLOWED_ORIGINS` in `.env` to
   your published extension's origin (`chrome-extension://<extension-id>`,
   visible on `chrome://extensions` after you load it) instead of `*`.
4. **Add basic abuse protection** before going public: a per-IP or
   per-extension-install rate limit (e.g. `slowapi`), and a request size cap
   on `question`, since every `/query` call costs you an LLM + embedding
   call.
5. **Point the extension at it** — open the extension's ⚙ settings and set
   the backend URL to your deployed HTTPS endpoint; add that domain to
   `host_permissions` in `manifest.json` and reload the extension.

## Publishing the extension

1. Add real icons (16/48/128 px) and reference them under an `"icons"` key
   in `manifest.json` — the Chrome Web Store requires them.
2. Zip the `extension/` folder's contents (not the folder itself).
3. Create a one-time $5 Chrome Web Store developer account, upload the zip,
   fill in the listing (screenshots, description, privacy disclosures for
   the data you send to your backend), and submit for review.

## Production hardening checklist

- Stream `/query` responses (Server-Sent Events or chunked HTTP) so answers
  appear token-by-token instead of after the full generation.
- Add a small reranker (e.g. Cohere rerank, or a cross-encoder) after the
  initial top-k retrieval if answers start citing loosely-related chunks.
- Log ingest/query latency and token counts so you can see cost per video
  and per question.
- Add an eviction policy (e.g. delete namespaces untouched for 30 days) so
  Pinecone usage doesn't grow unbounded.
- If you expect many simultaneous users, run the API behind a process
  manager (`uvicorn --workers N` or a Gunicorn+Uvicorn worker setup) rather
  than a single reload server.
