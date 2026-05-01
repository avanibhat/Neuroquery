import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# Paths
CHROMA_PATH      = str(BASE_DIR / "chroma_store")
DOCS_DIR         = BASE_DIR / "data" / "docs"
HISTORY_FILE     = BASE_DIR / "data" / "history.json"
FRONTEND_PATH    = BASE_DIR / "frontend" / "index.html"

# Models
BIOBERT_MODEL    = "dmis-lab/biobert-v1.1"
GROQ_MODEL       = "llama-3.3-70b-versatile"
COLLECTION_NAME  = "alzheimers_docs"

# Chunking
CHUNK_SIZE       = 300
CHUNK_OVERLAP    = 50

# Retrieval
DEFAULT_TOP_K    = 5

# PubMed
PUBMED_QUERY     = "Alzheimer's disease"
PUBMED_MAX       = 100

# API / credentials
GROQ_API_KEY     = os.getenv("GROQ_API_KEY")
ENTREZ_EMAIL     = os.getenv("ENTREZ_EMAIL", "researcher@example.com")
