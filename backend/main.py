import asyncio
import json
import logging
import logging.config
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import EVAL_FILES, FRONTEND_PATH, HISTORY_FILE, WEB_DIST_DIR
from retriever import retrieve, _get_collection, collection_stats
from llm import generate_response
from ingest import ingest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        col = _get_collection()
        if col.count() == 0:
            log.info("ChromaDB empty — running ingest on startup...")
            await asyncio.to_thread(ingest)
        else:
            log.info("ChromaDB ready (%d chunks).", col.count())
    except Exception as e:
        log.warning("Startup ingest check failed: %s", e)
    yield


app = FastAPI(title="Alzheimer's Research Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)


class Passage(BaseModel):
    """One retrieved chunk, returned so the UI can show the evidence behind an answer."""
    rank: int
    source: str
    text: str
    url: str | None = None


class Timing(BaseModel):
    retrieval_ms: int
    generation_ms: int


class ChatResponse(BaseModel):
    response: str
    sources: list[str]
    passages: list[Passage] = []
    timing: Timing | None = None


def source_url(source: str) -> str | None:
    """Map a source label like 'pubmed:12345' to a link the reader can check."""
    if source.startswith("pubmed:"):
        pmid = source.split(":", 1)[1].strip()
        if pmid.isdigit():
            return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return None


# ── API routes ───────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query must not be empty.")
    log.info("Chat request: %.80s", query)
    try:
        t0 = time.perf_counter()
        chunks = retrieve(query)
        t1 = time.perf_counter()
        answer = generate_response(query, chunks)
        t2 = time.perf_counter()

        # Keep retrieval order, drop duplicates
        sources = list(dict.fromkeys(c.get("source", "unknown") for c in chunks))
        passages = [
            Passage(
                rank=i + 1,
                source=c.get("source", "unknown"),
                text=c.get("text", ""),
                url=source_url(c.get("source", "")),
            )
            for i, c in enumerate(chunks)
        ]
        _save_history(query, answer, sources)
        return ChatResponse(
            response=answer,
            sources=sources,
            passages=passages,
            timing=Timing(
                retrieval_ms=round((t1 - t0) * 1000),
                generation_ms=round((t2 - t1) * 1000),
            ),
        )
    except Exception as e:
        log.error("Chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def run_ingest():
    log.info("Manual ingest triggered.")
    try:
        await asyncio.to_thread(ingest)
        return {"status": "done", "chunks": collection_stats()["total_chunks"]}
    except Exception as e:
        log.error("Ingest error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    return collection_stats()


@app.get("/eval")
def eval_results():
    """Aggregate scores from the LLM-as-judge evaluation, per retriever."""
    results = {}
    for name, path in EVAL_FILES.items():
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            results[name] = data.get("aggregate", {})
    return {"retrievers": results}


@app.get("/history")
def history(limit: int = 20):
    if not HISTORY_FILE.exists():
        return {"history": []}
    with open(HISTORY_FILE) as f:
        data = json.load(f)
    return {"history": data[-limit:]}


def _save_history(query: str, answer: str, sources: list[str]):
    data = []
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            data = json.load(f)
    data.append({
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "answer": answer,
        "sources": sources,
    })
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Frontend ─────────────────────────────────────────────────────────────────
# Serves the React build (web/dist) when it exists, otherwise the legacy
# vanilla JS page in frontend/index.html.

if (WEB_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST_DIR / "assets"), name="assets")


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    react_index = WEB_DIST_DIR / "index.html"
    if react_index.exists():
        return FileResponse(react_index)
    if FRONTEND_PATH.exists():
        return HTMLResponse(content=FRONTEND_PATH.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="No frontend build found")


@app.get("/legacy", response_class=HTMLResponse)
def serve_legacy_frontend():
    if not FRONTEND_PATH.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=FRONTEND_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
