import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from retriever import retrieve, _get_collection
from llm import generate_response
from ingest import ingest

FRONTEND_PATH = Path(__file__).parent.parent / "frontend" / "index.html"


# ---------------------------------------------------------------------------
# Startup: auto-ingest if collection is empty
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        collection = _get_collection()
        if collection.count() == 0:
            print("[startup] ChromaDB collection is empty — running ingest...")
            await asyncio.to_thread(ingest)
            print("[startup] Ingest complete.")
        else:
            print(f"[startup] ChromaDB ready ({collection.count()} chunks).")
    except Exception as e:
        print(f"[startup] Warning: could not check/run ingest: {e}")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Alzheimer's RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    sources: list[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    if not FRONTEND_PATH.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=FRONTEND_PATH.read_text(encoding="utf-8"))


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        chunks = retrieve(req.query)
        answer = generate_response(req.query, chunks)
        sources = list({c.get("source", "unknown") for c in chunks})
        return ChatResponse(response=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
def run_ingest():
    try:
        ingest()
        return {"status": "done"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
