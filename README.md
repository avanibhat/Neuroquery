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
│   ├── retriever.py   # BioBERT embedding + ChromaDB client
│   ├── llm.py         # Groq prompt builder + API call
│   └── config.py      # centralised settings
├── data/
│   └── docs/          # Drop PDFs here for local ingestion
├── frontend/
│   └── index.html     # Chat UI (vanilla JS)
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
└── README.md
```
