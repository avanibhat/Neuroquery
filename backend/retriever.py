"""
retriever.py — BioBERT-based embedding + ChromaDB retrieval.

Embeds text using dmis-lab/biobert-v1.1 with mean pooling of the last
hidden state. ChromaDB stores vectors persistently at ./chroma_store.
"""

from pathlib import Path

import torch
import chromadb
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

MODEL_NAME = "dmis-lab/biobert-v1.1"
CHROMA_PATH = str(Path(__file__).parent.parent / "chroma_store")
COLLECTION_NAME = "alzheimers_docs"

# ---------------------------------------------------------------------------
# Model (lazy-loaded once)
# ---------------------------------------------------------------------------

_tokenizer = None
_model = None


def _load_model():
    global _tokenizer, _model
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModel.from_pretrained(MODEL_NAME)
        _model.eval()


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed(text: str) -> list[float]:
    """Return a mean-pooled BioBERT embedding for the given text."""
    _load_model()
    inputs = _tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True,
    )
    with torch.no_grad():
        outputs = _model(**inputs)

    # Mean pool last hidden state, ignoring padding tokens
    last_hidden = outputs.last_hidden_state          # (1, seq_len, hidden)
    attention_mask = inputs["attention_mask"]        # (1, seq_len)
    mask_expanded = attention_mask.unsqueeze(-1).float()
    sum_hidden = (last_hidden * mask_expanded).sum(dim=1)
    sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
    pooled = (sum_hidden / sum_mask).squeeze(0)      # (hidden,)
    return pooled.tolist()


# ---------------------------------------------------------------------------
# ChromaDB client
# ---------------------------------------------------------------------------

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        # No built-in embedding function — we supply embeddings manually
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_documents(chunks: list[dict]) -> None:
    """
    Embed and store document chunks in ChromaDB.

    Args:
        chunks: list of {"text": str, "source": str}
    """
    collection = _get_collection()
    existing_count = collection.count()

    ids = [f"doc_{existing_count + i}" for i in range(len(chunks))]
    documents = [c["text"] for c in chunks]
    metadatas = [{"source": c.get("source", "unknown")} for c in chunks]

    embeddings = [
        embed(c["text"])
        for c in tqdm(chunks, desc="Embedding chunks", unit="chunk", colour="green")
    ]

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )


def retrieve(query: str, n_results: int = 5) -> list[dict]:
    """
    Return the top n_results chunks most relevant to the query.

    Returns:
        list of {"text": str, "source": str}
    """
    collection = _get_collection()
    query_embedding = embed(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas"],
    )

    docs = []
    for text, meta in zip(results["documents"][0], results["metadatas"][0]):
        docs.append({"text": text, "source": meta.get("source", "unknown")})
    return docs
