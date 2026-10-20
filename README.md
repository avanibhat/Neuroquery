---
title: NeuroQuery
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Alzheimer's Disease Research Assistant

🧠 **Live demo:** [https://avanibhat-neuroquery.hf.space](https://avanibhat-neuroquery.hf.space)

A Retrieval-Augmented Generation (RAG) system for querying Alzheimer's disease
research literature. Combines biomedical-domain embeddings (BioBERT), semantic
vector search (ChromaDB), and a free LLM (Groq / Llama 3.3 70B) to give
grounded, source-cited answers to research questions.

![NeuroQuery answer with clickable citations and the evidence panel](docs/screenshot.png)

> All answers are backed by PubMed abstracts and optional local PDFs.  
> No data is stored externally — your documents stay on your machine.

---

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │              Data Sources               │
                        │  PubMed / Entrez API   Local PDFs       │
                        └────────────┬───────────────┬────────────┘
                                     │               │
                                     ▼               ▼
                        ┌─────────────────────────────────────────┐
                        │              ingest.py                  │
                        │  Fetch abstracts · Extract PDF text     │
                        │  Chunk (300 tokens, 50 overlap)         │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │             retriever.py                │
                        │  BioBERT (dmis-lab/biobert-v1.1)        │
                        │  Mean-pool last hidden state → vector   │
                        │  ChromaDB  (persistent, cosine)         │
                        └────────────────────┬────────────────────┘
                                             │
                          ┌──────────────────┘
                          │  Top-k chunks + source labels
                          ▼
         ┌─────────────────────────────────────────────────┐
         │                   llm.py                        │
         │  System prompt: AD specialist                   │
         │  Numbered context blocks injected into prompt   │
         │  Groq — Llama 3.3 70B  (free tier)             │
         └──────────────────────┬──────────────────────────┘
                                │
                                ▼
         ┌─────────────────────────────────────────────────┐
         │                  main.py  (FastAPI)             │
         │  GET  /          → React app (web/dist)         │
         │  POST /chat      → answer + passages + timing   │
         │  GET  /eval      → evaluation scores            │
         │  POST /ingest    → re-run ingestion pipeline    │
         └──────────────────────┬──────────────────────────┘
                                │
                                ▼
         ┌─────────────────────────────────────────────────┐
         │        web/  (React + TypeScript, Vite)         │
         │  Chat · clickable citations · evidence panel    │
         └─────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component    | Technology                       | Role                                      |
|--------------|----------------------------------|-------------------------------------------|
| Embeddings   | BioBERT `dmis-lab/biobert-v1.1`  | Domain-specific biomedical text encoding  |
| Vector store | ChromaDB (persistent, cosine)    | Semantic similarity search                |
| LLM          | Groq — Llama 3.3 70B (free)     | Grounded answer generation                |
| Literature   | PubMed via Biopython Entrez API  | Open-access Alzheimer's abstracts         |
| Local docs   | pypdf                            | Extract text from researcher-supplied PDFs|
| API server   | FastAPI + Uvicorn                | REST endpoints + static frontend serving  |
| Frontend     | React 18 + TypeScript (Vite)     | Chat UI with citation-linked evidence panel |
| Testing      | pytest · Vitest + Testing Library | API contract and UI behaviour tests       |

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/avanibhat/neuroquery.git
cd neuroquery
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> First run downloads the BioBERT model weights (~440 MB) automatically.

### 3. Get a free Groq API key

1. Go to [console.groq.com](https://console.groq.com) and sign up (free, no credit card)
2. Navigate to **API Keys** → **Create API Key**
3. Copy the key

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=gsk_...
ENTREZ_EMAIL=you@example.com
# Optional: override the Groq model (default: llama-3.3-70b-versatile)
# GROQ_MODEL=openai/gpt-oss-120b
```

`GROQ_MODEL` is optional. If your Groq key can't access the default model, set it to another model your key can use. On Hugging Face Spaces, add it under **Settings → Variables and secrets**.

### 5. (Optional) Add local PDFs

Drop any Alzheimer's research PDFs into `data/docs/`.

### 6. Ingest documents

```bash
python backend/ingest.py
```

Fetches 500 PubMed abstracts, embeds everything with BioBERT, stores vectors in `chroma_store/`. Takes ~5–15 minutes on CPU (one-time).

### 7. Start the server

**Mac / Linux:**
```bash
PYTHONPATH=backend uvicorn backend.main:app --reload
```

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH="backend"; uvicorn backend.main:app --reload
```

### 8. Build or run the frontend

The UI lives in `web/` (React + TypeScript, needs Node 20+).

```bash
cd web
npm ci
npm run build      # outputs web/dist, which FastAPI serves at /
```

Open [http://localhost:8000](http://localhost:8000).

For frontend development with hot reload, keep the backend running and start Vite in a second terminal:

```bash
cd web
npm run dev        # http://localhost:5173, API calls are proxied to :8000
```

The original vanilla JS page is still available at `/legacy`.

### Run with Docker

```bash
docker build -t neuroquery .
docker run -p 7860:7860 --env-file .env neuroquery
```

The Dockerfile builds the frontend in a Node stage and copies only the static build into the Python image.

---

## Frontend

The interface is built around one question: **can the reader check where an answer came from?**

- **Clickable citations.** The LLM cites context blocks inline as `[1]`, `[2, 4]`. Each marker becomes a button that scrolls to and highlights the exact passage it refers to.
- **Evidence panel.** Every retrieved passage is shown next to the answer, marked *cited* or *not cited*, with a link to the PubMed record. Unused passages make retrieval misses visible instead of hiding them.
- **Reliability view.** Shows the BioBERT vs TF-IDF evaluation scores from `/eval`, so users see how far to trust answers.
- **Robust request handling.** Typed API client with timeouts, a Stop button (AbortController), readable error messages from FastAPI and Groq rate limits, and one-click retry.
- **History.** Conversations are kept per browser in localStorage, with safe fallbacks when storage is unavailable.
- **Responsive.** On narrow screens the sidebar collapses and the evidence panel becomes a drawer.

```
web/src/
├── App.tsx                 # state, request lifecycle, layout
├── types.ts                # mirrors the Pydantic response models
├── lib/api.ts              # typed fetch client: timeouts, cancellation, error parsing
├── lib/citations.ts        # parse [n] markers and link them to passages
├── lib/useSessions.ts      # conversation history hook
└── components/             # AnswerMessage, EvidencePanel, EvalCard, Composer, Sidebar
```

---

## Groq Free Tier Limits

| Limit | Amount |
|-------|--------|
| Requests per minute | 30 |
| Requests per day | 1,000 |
| Tokens per minute | 12,000 |

Sufficient for individual or small-group research use.

---

## Project Focus & FAIR Data Principles

This project is scoped exclusively to **Alzheimer's Disease (AD)** research.

| Principle    | Implementation                                                               |
|--------------|------------------------------------------------------------------------------|
| Findable     | Every answer cites its source (`pubmed:{pmid}` or `pdf:{filename}`)          |
| Accessible   | PubMed abstracts retrieved via the open Entrez API; no paywalled content     |
| Interoperable| Standard REST API; plain JSON responses consumable by any downstream tool    |
| Reusable     | ChromaDB store is persistent and portable; re-ingest is a single command     |

---

## Project Structure

```
neuroquery/
├── backend/
│   ├── main.py        # FastAPI app (routes, startup, CORS)
│   ├── ingest.py      # PubMed fetch + PDF loader + chunking
│   ├── retriever.py   # BioBERT + TF-IDF retrieval, ChromaDB client
│   ├── llm.py         # Groq prompt builder + API call
│   ├── eval.py        # LLM-as-judge evaluation pipeline
│   └── config.py      # centralised settings
├── tests/
│   ├── test_chunking.py   # chunking overlap correctness
│   ├── test_embed.py      # BioBERT embedding dimensionality
│   ├── test_api.py        # FastAPI /stats and /history endpoints
│   └── test_chat.py       # /chat contract: passages, citations, timing, errors
├── data/
│   └── docs/          # Drop PDFs here for local ingestion
├── web/               # React + TypeScript frontend (Vite, Vitest)
├── frontend/
│   └── index.html     # legacy vanilla JS UI, served at /legacy
├── mcp_server.py      # MCP server — exposes RAG tools via Model Context Protocol
├── requirements.txt   # pinned dependencies
├── Makefile           # ingest / eval / test / web-build / web-test
├── EVALUATION.md      # retriever comparison methodology and results
├── .env.example
├── .gitignore
├── Dockerfile
└── README.md
```

---

## Evaluation

The project includes an LLM-as-judge evaluation pipeline comparing two retrieval strategies across 20 Alzheimer's research questions.

### Metrics

| Metric | What it measures |
|--------|-----------------|
| **Precision@5** | Fraction of the 5 retrieved chunks judged relevant to the question |
| **MRR** | Mean Reciprocal Rank — 1/rank of the first relevant chunk |
| **Hit Rate** | Fraction of questions with at least one relevant chunk in top 5 |
| **Faithfulness** | 0–1 score: how well the answer is grounded in retrieved context (detects hallucination) |
| **Completeness** | Binary: does the answer appropriately address the question? |

### Retrievers compared

| Retriever | Method |
|-----------|--------|
| **BioBERT** | Dense semantic search via `dmis-lab/biobert-v1.1` embeddings + ChromaDB |
| **TF-IDF** | Sparse keyword search via `sklearn.TfidfVectorizer` + cosine similarity |

### Running

```bash
make eval           # BioBERT retriever — 20 questions (~10 min)
make eval-tfidf     # TF-IDF retriever  — 20 questions (~5 min)
make eval-compare   # side-by-side comparison table

# Quick sanity check (3 questions)
python backend/eval.py --dry-run

# Resume if interrupted by Groq rate limits
python backend/eval.py --resume
```

Results are saved to `eval_results_biobert.json` / `eval_results_tfidf.json`. Full scores and methodology in [EVALUATION.md](EVALUATION.md).

### Questions covered

20 questions across 5 categories: biomarkers, genetics, therapeutics, mechanisms, diagnostics.

---

## Results

Evaluated on 20 questions across 5 categories (biomarkers, genetics, therapeutics,
mechanisms, diagnostics), judged by Llama 3.3 70B, against the 500-abstract corpus.

| Metric | BioBERT | TF-IDF |
|--------|---------|--------|
| Mean Precision@5 | 0.26 | 0.27 |
| Mean MRR | 0.48 | 0.53 |
| Hit Rate | 70% | 65% |
| Mean Faithfulness | 0.33 | 0.46 |
| Completeness Rate | 90% | 90% |

The two retrievers perform comparably overall but diverge on individual questions —
BioBERT wins on synonym-heavy phrasing, TF-IDF wins when the question's wording
matches the source text closely. See [EVALUATION.md](EVALUATION.md) for the
per-question breakdown and analysis.

---

## MCP Server (Model Context Protocol)

NeuroQuery also ships as an **MCP server**, letting any MCP-compatible client
(Claude Desktop, VS Code Copilot, custom agents) use the RAG pipeline as a tool.

### Available tools

| Tool | Description |
|------|-------------|
| `search_literature` | BioBERT semantic search over the indexed corpus |
| `search_literature_tfidf` | TF-IDF keyword search (baseline) |
| `ask_research_question` | Full RAG pipeline — retrieve + generate a grounded answer |
| `get_collection_stats` | Number of indexed chunks and collection info |
| `ingest_documents` | Trigger document ingestion from PubMed / local PDFs |

### Quick start

```bash
pip install "mcp[cli]>=1.0.0"
python mcp_server.py
```

### Claude Desktop configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "neuroquery": {
      "command": "python",
      "args": ["/absolute/path/to/alzheimers-rag/mcp_server.py"],
      "env": {
        "GROQ_API_KEY": "gsk_..."
      }
    }
  }
}
```

Once connected, Claude can search Alzheimer's literature and answer research
questions using the same BioBERT + ChromaDB pipeline that powers the web UI.

---

## Limitations and Future Work

### Current limitations

**Corpus size** — The system indexes ~500 PubMed abstracts, which covers common Alzheimer's topics well but may lack depth on niche subtopics (e.g. rare genetic variants, very recent clinical trial results). Abstracts are also shorter and less detailed than full-text papers.

**LLM-as-judge reliability** — Using the same LLM (Llama 3.3 70B via Groq) for both answer generation and evaluation introduces self-consistency bias: the judge may rate answers highly because they match its own generation style, not because they are factually correct. A human evaluation pass on a sample would give a more reliable ground truth.

**Chunk size sensitivity** — The 300-token chunk size with 50-token overlap was chosen heuristically. Longer abstracts may be split at semantically awkward boundaries; shorter chunks could miss context needed for multi-sentence reasoning. Systematic ablation over chunk sizes has not been run.

**No full-text access** — Only PubMed abstracts are ingested. Full papers (via PubMed Central Open Access) would substantially increase the depth of retrievable evidence.

### Future work

- **Hybrid retrieval** — Combine BioBERT and TF-IDF scores with Reciprocal Rank Fusion (RRF) for better coverage of both semantic similarity and keyword matching
- **Re-ranking** — Add a cross-encoder reranker (e.g. `cross-encoder/ms-marco-MiniLM`) to score the top-20 candidates before returning top-5
- **Full-text ingestion** — Expand to PubMed Central Open Access full-text XML for richer context
- **Query expansion** — Use the LLM to generate alternative phrasings of the user's question before retrieval to improve recall
- **Persistent vector store on HF Spaces** — Mount a HuggingFace Dataset as the ChromaDB backing store so the index survives Space restarts
