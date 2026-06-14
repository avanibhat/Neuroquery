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
         │  GET  /          → frontend/index.html          │
         │  POST /chat      → retrieve + generate          │
         │  POST /ingest    → re-run ingestion pipeline    │
         └──────────────────────┬──────────────────────────┘
                                │
                                ▼
         ┌─────────────────────────────────────────────────┐
         │           frontend/index.html                   │
         │  Vanilla JS chat UI · Source chips · Re-index   │
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
| Frontend     | Vanilla HTML / CSS / JS          | Zero-dependency chat interface            |

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
```

### 5. (Optional) Add local PDFs

Drop any Alzheimer's research PDFs into `data/docs/`.

### 6. Ingest documents

```bash
python backend/ingest.py
```

Fetches 100 PubMed abstracts, embeds everything with BioBERT, stores vectors in `chroma_store/`. Takes ~5–15 minutes on CPU (one-time).

### 7. Start the server

**Mac / Linux:**
```bash
PYTHONPATH=backend uvicorn backend.main:app --reload
```

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH="backend"; uvicorn backend.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

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
│   └── test_api.py        # FastAPI /stats and /history endpoints
├── data/
│   └── docs/          # Drop PDFs here for local ingestion
├── frontend/
│   └── index.html     # Chat UI (vanilla JS, dark/light mode)
├── requirements.txt   # pinned dependencies
├── Makefile           # ingest / eval / eval-tfidf / eval-compare / test
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

*Run `make eval && make eval-tfidf && make eval-compare` to populate.*

| Metric | BioBERT | TF-IDF |
|--------|---------|--------|
| Mean Precision@5 | — | — |
| Mean MRR | — | — |
| Hit Rate | — | — |
| Mean Faithfulness | — | — |
| Completeness Rate | — | — |

See [EVALUATION.md](EVALUATION.md) for the per-question breakdown and analysis.

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
