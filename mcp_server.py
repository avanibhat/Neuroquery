"""MCP Server for NeuroQuery — Alzheimer's Research RAG Pipeline.

Exposes the RAG pipeline as MCP tools, allowing any MCP-compatible
LLM client (Claude Desktop, VS Code, etc.) to search Alzheimer's
research literature, ask questions, and get grounded answers.

Usage:
    python mcp_server.py

Then add to your MCP client config (e.g. Claude Desktop):
{
    "mcpServers": {
        "neuroquery": {
            "command": "python",
            "args": ["/path/to/alzheimers-rag/mcp_server.py"]
        }
    }
}
"""

import os
import sys
import json
import logging

# Ensure backend modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- Initialize MCP server ---
mcp = FastMCP(
    "NeuroQuery",
    description="Alzheimer's Disease research assistant — search biomedical literature, "
                "ask research questions, and get grounded answers from a BioBERT + ChromaDB RAG pipeline.",
)


# --- MCP Tools ---

@mcp.tool()
def search_literature(query: str, top_k: int = 5) -> str:
    """Search the Alzheimer's research literature using BioBERT semantic retrieval.

    Returns the most relevant text chunks from the indexed corpus,
    ranked by cosine similarity to the query embedding.

    Args:
        query: A biomedical research question or topic (e.g., "amyloid beta aggregation mechanisms").
        top_k: Number of results to return (default 5, max 20).
    """
    from retriever import retrieve

    top_k = min(top_k, 20)
    chunks = retrieve(query, n_results=top_k)

    results = []
    for i, chunk in enumerate(chunks, 1):
        results.append({
            "rank": i,
            "source": chunk.get("source", "unknown"),
            "text": chunk["text"][:500],  # Cap text length
        })

    return json.dumps({
        "query": query,
        "num_results": len(results),
        "results": results,
    }, indent=2)


@mcp.tool()
def search_literature_tfidf(query: str, top_k: int = 5) -> str:
    """Search using TF-IDF keyword matching (baseline retriever).

    Useful for comparison with the BioBERT semantic search,
    or when exact keyword matching is preferred.

    Args:
        query: A biomedical research question or keywords.
        top_k: Number of results to return (default 5, max 20).
    """
    from retriever import retrieve_tfidf

    top_k = min(top_k, 20)
    chunks = retrieve_tfidf(query, n_results=top_k)

    results = []
    for i, chunk in enumerate(chunks, 1):
        results.append({
            "rank": i,
            "source": chunk.get("source", "unknown"),
            "text": chunk["text"][:500],
        })

    return json.dumps({
        "query": query,
        "retriever": "tfidf",
        "num_results": len(results),
        "results": results,
    }, indent=2)


@mcp.tool()
def ask_research_question(question: str, top_k: int = 5) -> str:
    """Ask a question about Alzheimer's Disease and get a grounded answer.

    This performs the full RAG pipeline:
    1. Retrieves relevant chunks from the literature using BioBERT
    2. Sends the question + context to Llama 3.3 70B via Groq
    3. Returns a grounded answer with source citations

    Args:
        question: A research question about Alzheimer's Disease.
        top_k: Number of context chunks to retrieve (default 5).
    """
    from retriever import retrieve
    from llm import generate_response

    chunks = retrieve(question, n_results=min(top_k, 10))
    answer = generate_response(question, chunks)
    sources = list({c.get("source", "unknown") for c in chunks})

    return json.dumps({
        "question": question,
        "answer": answer,
        "sources": sources,
        "num_chunks_used": len(chunks),
    }, indent=2)


@mcp.tool()
def get_collection_stats() -> str:
    """Get statistics about the indexed document collection.

    Returns the total number of chunks in the ChromaDB vector store
    and the collection name.
    """
    from retriever import collection_stats

    stats = collection_stats()
    return json.dumps(stats, indent=2)


@mcp.tool()
def ingest_documents() -> str:
    """Ingest new documents into the vector store.

    Fetches Alzheimer's Disease abstracts from PubMed, chunks them,
    embeds with BioBERT, and stores in ChromaDB. Safe to call
    multiple times — new documents are appended.
    """
    from ingest import ingest
    from retriever import collection_stats

    ingest()
    stats = collection_stats()
    return json.dumps({
        "status": "complete",
        "total_chunks": stats["total_chunks"],
    }, indent=2)


# --- MCP Resources ---

@mcp.resource("neuroquery://stats")
def stats_resource() -> str:
    """Current collection statistics."""
    from retriever import collection_stats
    return json.dumps(collection_stats(), indent=2)


# --- Run ---
if __name__ == "__main__":
    mcp.run()
