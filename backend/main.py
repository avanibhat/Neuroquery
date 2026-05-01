import asyncio
import json
import logging
import logging.config
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from config import FRONTEND_PATH, HISTORY_FILE
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


class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    sources: list[str]


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    if not FRONTEND_PATH.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=FRONTEND_PATH.read_text(encoding="utf-8"))


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    log.info("Chat request: %.80s", req.query)
    try:
        chunks = retrieve(req.query)
        answer = generate_response(req.query, chunks)
        sources = list({c.get("source", "unknown") for c in chunks})
        _save_history(req.query, answer, sources)
        return ChatResponse(response=answer, sources=sources)
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


@app.get("/stats")
def stats():
    return collection_stats()


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
