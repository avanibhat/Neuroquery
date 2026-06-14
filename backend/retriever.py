import logging

import numpy as np
import torch
import chromadb
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

from config import BIOBERT_MODEL, CHROMA_PATH, COLLECTION_NAME, DEFAULT_TOP_K

log = logging.getLogger(__name__)

# ── BioBERT ─────────────────────────────────────────────────────────────────

_tokenizer  = None
_model      = None
_client     = None
_collection = None


def _load_model():
    global _tokenizer, _model
    if _tokenizer is None:
        log.info("Loading BioBERT model: %s", BIOBERT_MODEL)
        _tokenizer = AutoTokenizer.from_pretrained(BIOBERT_MODEL)
        _model     = AutoModel.from_pretrained(BIOBERT_MODEL)
        _model.eval()
        log.info("BioBERT loaded.")


def embed(text: str) -> list[float]:
    _load_model()
    inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
    with torch.no_grad():
        outputs = _model(**inputs)
    last_hidden   = outputs.last_hidden_state
    mask_expanded = inputs["attention_mask"].unsqueeze(-1).float()
    pooled = (last_hidden * mask_expanded).sum(dim=1) / mask_expanded.sum(dim=1).clamp(min=1e-9)
    return pooled.squeeze(0).tolist()


# ── ChromaDB ─────────────────────────────────────────────────────────────────

def _get_collection():
    global _client, _collection
    if _collection is None:
        log.info("Connecting to ChromaDB at %s", CHROMA_PATH)
        _client     = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("Collection '%s' ready (%d chunks).", COLLECTION_NAME, _collection.count())
    return _collection


def add_documents(chunks: list[dict]) -> None:
    collection = _get_collection()
    existing   = collection.count()
    log.info("Embedding %d chunks (existing: %d)...", len(chunks), existing)

    ids        = [f"doc_{existing + i}" for i in range(len(chunks))]
    documents  = [c["text"] for c in chunks]
    metadatas  = [{"source": c.get("source", "unknown")} for c in chunks]
    embeddings = [
        embed(c["text"])
        for c in tqdm(chunks, desc="Embedding chunks", unit="chunk", colour="green")
    ]

    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    log.info("Stored %d chunks. Total: %d.", len(chunks), collection.count())


def retrieve(query: str, n_results: int = DEFAULT_TOP_K) -> list[dict]:
    """BioBERT semantic retrieval."""
    collection = _get_collection()
    log.info("BioBERT retrieving top-%d for: %.80s", n_results, query)
    results = collection.query(
        query_embeddings=[embed(query)],
        n_results=n_results,
        include=["documents", "metadatas"],
    )
    docs = [
        {"text": text, "source": meta.get("source", "unknown")}
        for text, meta in zip(results["documents"][0], results["metadatas"][0])
    ]
    log.info("Retrieved %d chunks.", len(docs))
    return docs


def collection_stats() -> dict:
    collection = _get_collection()
    return {"total_chunks": collection.count(), "collection": COLLECTION_NAME}


# ── TF-IDF retriever ─────────────────────────────────────────────────────────

_tfidf_vectorizer = None
_tfidf_matrix     = None
_tfidf_docs: list[dict] = []


def _build_tfidf():
    global _tfidf_vectorizer, _tfidf_matrix, _tfidf_docs
    log.info("Building TF-IDF index from ChromaDB...")
    collection = _get_collection()
    result     = collection.get(include=["documents", "metadatas"])

    documents  = result["documents"]
    metadatas  = result["metadatas"]
    _tfidf_docs = [
        {"text": d, "source": m.get("source", "unknown")}
        for d, m in zip(documents, metadatas)
    ]

    _tfidf_vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
    _tfidf_matrix     = _tfidf_vectorizer.fit_transform(documents)
    log.info("TF-IDF index built: %d documents, %d features.",
             len(documents), _tfidf_matrix.shape[1])


def retrieve_tfidf(query: str, n_results: int = DEFAULT_TOP_K) -> list[dict]:
    """TF-IDF keyword retrieval over the same ChromaDB corpus."""
    if _tfidf_vectorizer is None:
        _build_tfidf()

    log.info("TF-IDF retrieving top-%d for: %.80s", n_results, query)
    query_vec = _tfidf_vectorizer.transform([query])
    scores    = cosine_similarity(query_vec, _tfidf_matrix)[0]
    top_idx   = np.argsort(scores)[::-1][:n_results]

    docs = [_tfidf_docs[i] for i in top_idx if scores[i] > 0]
    log.info("TF-IDF retrieved %d chunks.", len(docs))
    return docs
