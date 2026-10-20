# ── Stage 1: build the React + TypeScript frontend ───────────────────────────
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# ── Stage 2: Python API ──────────────────────────────────────────────────────
FROM python:3.11-slim

# System dependencies required by torch and chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer-cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/   ./backend/
COPY frontend/  ./frontend/
COPY data/      ./data/
COPY eval_results_biobert.json eval_results_tfidf.json ./

# Built frontend from stage 1 (served by FastAPI at /)
COPY --from=web /web/dist ./web/dist

# Set PYTHONPATH so backend modules resolve correctly
ENV PYTHONPATH=/app/backend

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
