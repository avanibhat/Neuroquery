"""
ingest.py — Ingest documents from PubMed and local PDFs into ChromaDB.

Sources:
  1. PubMed: top 100 abstracts for "Alzheimer's disease" via Entrez API
  2. Local PDFs: all .pdf files under ./data/docs/

Run directly: python backend/ingest.py
"""

import os
import glob
import time
from pathlib import Path

from Bio import Entrez
from pypdf import PdfReader
from dotenv import load_dotenv
from tqdm import tqdm

from retriever import add_documents

load_dotenv()

DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"
PUBMED_QUERY = "Alzheimer's disease"
PUBMED_MAX = 100
CHUNK_TOKENS = 300
CHUNK_OVERLAP = 50

# Entrez requires a contact email
Entrez.email = os.getenv("ENTREZ_EMAIL", "researcher@example.com")


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk(text: str, size: int = CHUNK_TOKENS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping token-sized chunks (whitespace tokens)."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Source 1: PubMed
# ---------------------------------------------------------------------------

def fetch_pubmed(query: str = PUBMED_QUERY, max_results: int = PUBMED_MAX) -> list[dict]:
    """
    Search PubMed and return chunked abstracts.

    Returns list of {"text": str, "source": "pubmed:{pmid}"}
    """
    print(f"[PubMed] Searching: '{query}' (max {max_results})")
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()

    pmids = record["IdList"]
    print(f"[PubMed] Found {len(pmids)} PMIDs")

    chunks = []
    # Fetch in batches of 20 to be polite to NCBI
    batch_size = 20
    num_batches = -(-len(pmids) // batch_size)  # ceil division
    with tqdm(total=len(pmids), desc="Fetching PubMed abstracts", unit="article", colour="cyan") as pbar:
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i : i + batch_size]
            handle = Entrez.efetch(
                db="pubmed",
                id=",".join(batch),
                rettype="abstract",
                retmode="xml",
            )
            records = Entrez.read(handle)
            handle.close()

            for article in records["PubmedArticle"]:
                try:
                    pmid = str(article["MedlineCitation"]["PMID"])
                    abstract_obj = (
                        article["MedlineCitation"]["Article"]
                        .get("Abstract", {})
                        .get("AbstractText", [])
                    )
                    if isinstance(abstract_obj, list):
                        abstract = " ".join(str(s) for s in abstract_obj)
                    else:
                        abstract = str(abstract_obj)

                    abstract = abstract.strip()
                    if not abstract:
                        continue

                    for chunk in _chunk(abstract):
                        chunks.append({"text": chunk, "source": f"pubmed:{pmid}"})
                except (KeyError, IndexError):
                    continue

            pbar.update(len(batch))
            pbar.set_postfix(chunks=len(chunks), batch=f"{i // batch_size + 1}/{num_batches}")
            time.sleep(0.34)  # Stay under NCBI's 3 req/s limit

    print(f"[PubMed] Total chunks: {len(chunks)}")
    return chunks


# ---------------------------------------------------------------------------
# Source 2: Local PDFs
# ---------------------------------------------------------------------------

def load_pdfs(docs_dir: Path = DOCS_DIR) -> list[dict]:
    """
    Extract text from all PDFs in docs_dir and return chunked passages.

    Returns list of {"text": str, "source": "pdf:{filename}"}
    """
    pdf_files = glob.glob(str(docs_dir / "**/*.pdf"), recursive=True)
    if not pdf_files:
        print(f"[PDF] No PDF files found in {docs_dir}")
        return []

    print(f"[PDF] Found {len(pdf_files)} PDF(s)")
    chunks = []
    for filepath in pdf_files:
        filename = os.path.basename(filepath)
        try:
            reader = PdfReader(filepath)
            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            ).strip()
            if not text:
                print(f"[PDF] Skipping {filename} — no extractable text")
                continue
            file_chunks = _chunk(text)
            for chunk in file_chunks:
                chunks.append({"text": chunk, "source": f"pdf:{filename}"})
            print(f"[PDF] {filename}: {len(file_chunks)} chunks")
        except Exception as e:
            print(f"[PDF] Error reading {filename}: {e}")

    print(f"[PDF] Total chunks: {len(chunks)}")
    return chunks


# ---------------------------------------------------------------------------
# Main ingest
# ---------------------------------------------------------------------------

def ingest():
    all_chunks: list[dict] = []

    pubmed_chunks = fetch_pubmed()
    all_chunks.extend(pubmed_chunks)

    pdf_chunks = load_pdfs()
    all_chunks.extend(pdf_chunks)

    if not all_chunks:
        print("Nothing to ingest.")
        return

    print(f"\nEmbedding and storing {len(all_chunks)} total chunks — this may take a while...")
    add_documents(all_chunks)
    print("Ingestion complete.")


if __name__ == "__main__":
    ingest()
