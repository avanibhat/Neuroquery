import logging
import os
import glob
import time

from Bio import Entrez
from pypdf import PdfReader
from tqdm import tqdm

from config import (
    DOCS_DIR, PUBMED_QUERY, PUBMED_MAX,
    CHUNK_SIZE, CHUNK_OVERLAP, ENTREZ_EMAIL
)
from retriever import add_documents

log = logging.getLogger(__name__)
Entrez.email = ENTREZ_EMAIL


def _chunk(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split on sentence boundaries where possible, then fall back to word-level chunks."""
    import re
    # Split into sentences first
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, current_words = [], []

    for sentence in sentences:
        words = sentence.split()
        if len(current_words) + len(words) > size and current_words:
            chunks.append(" ".join(current_words))
            current_words = current_words[-overlap:]
        current_words.extend(words)

    if current_words:
        chunks.append(" ".join(current_words))
    return chunks


def fetch_pubmed(query: str = PUBMED_QUERY, max_results: int = PUBMED_MAX) -> list[dict]:
    log.info("Searching PubMed: '%s' (max %d)", query, max_results)
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()

    pmids      = record["IdList"]
    batch_size = 20
    num_batches = -(-len(pmids) // batch_size)
    chunks     = []

    log.info("Found %d PMIDs. Fetching in %d batches...", len(pmids), num_batches)
    with tqdm(total=len(pmids), desc="Fetching PubMed abstracts", unit="article", colour="cyan") as pbar:
        for i in range(0, len(pmids), batch_size):
            batch  = pmids[i : i + batch_size]
            handle = Entrez.efetch(db="pubmed", id=",".join(batch), rettype="abstract", retmode="xml")
            records = Entrez.read(handle)
            handle.close()

            for article in records["PubmedArticle"]:
                try:
                    pmid         = str(article["MedlineCitation"]["PMID"])
                    abstract_obj = article["MedlineCitation"]["Article"].get("Abstract", {}).get("AbstractText", [])
                    abstract     = " ".join(str(s) for s in abstract_obj) if isinstance(abstract_obj, list) else str(abstract_obj)
                    abstract     = abstract.strip()
                    if not abstract:
                        continue
                    for chunk in _chunk(abstract):
                        chunks.append({"text": chunk, "source": f"pubmed:{pmid}"})
                except (KeyError, IndexError):
                    continue

            pbar.update(len(batch))
            pbar.set_postfix(chunks=len(chunks), batch=f"{i // batch_size + 1}/{num_batches}")
            time.sleep(0.34)

    log.info("PubMed: %d chunks from %d articles.", len(chunks), len(pmids))
    return chunks


def load_pdfs() -> list[dict]:
    pdf_files = glob.glob(str(DOCS_DIR / "**/*.pdf"), recursive=True)
    if not pdf_files:
        log.info("No PDFs found in %s", DOCS_DIR)
        return []

    chunks = []
    for filepath in tqdm(pdf_files, desc="Loading PDFs", unit="file", colour="yellow"):
        filename = os.path.basename(filepath)
        try:
            reader = PdfReader(filepath)
            text   = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if not text:
                log.warning("No extractable text in %s", filename)
                continue
            file_chunks = _chunk(text)
            for chunk in file_chunks:
                chunks.append({"text": chunk, "source": f"pdf:{filename}"})
            log.info("%s → %d chunks", filename, len(file_chunks))
        except Exception as e:
            log.error("Error reading %s: %s", filename, e)

    log.info("PDFs: %d total chunks.", len(chunks))
    return chunks


def ingest():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    all_chunks = fetch_pubmed() + load_pdfs()
    if not all_chunks:
        log.warning("Nothing to ingest.")
        return
    log.info("Total chunks to embed: %d", len(all_chunks))
    add_documents(all_chunks)
    log.info("Ingestion complete.")


if __name__ == "__main__":
    ingest()
