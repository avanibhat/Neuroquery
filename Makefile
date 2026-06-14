# Alzheimer's RAG — Makefile
# Requires: make (Git Bash on Windows, or native on Mac/Linux)
#
# Usage:
#   make ingest           — fetch 500 PubMed abstracts and embed with BioBERT
#   make eval             — run full BioBERT evaluation (20 questions)
#   make eval-tfidf       — run full TF-IDF evaluation (20 questions)
#   make eval-compare     — print side-by-side comparison of both retrievers
#   make test             — run pytest suite

PYTHONPATH := backend
PYTHON     := python

export PYTHONPATH

.PHONY: ingest eval eval-tfidf eval-compare test

ingest:
	$(PYTHON) backend/ingest.py

eval:
	$(PYTHON) backend/eval.py --retriever biobert

eval-tfidf:
	$(PYTHON) backend/eval.py --retriever tfidf

eval-compare:
	@$(PYTHON) - <<'EOF'
import json, sys
from pathlib import Path

root = Path(".")
files = {
    "biobert": root / "eval_results_biobert.json",
    "tfidf":   root / "eval_results_tfidf.json",
}

data = {}
for name, path in files.items():
    if not path.exists():
        print(f"[missing] {path} — run 'make eval' and 'make eval-tfidf' first.")
        sys.exit(1)
    with open(path) as f:
        data[name] = json.load(f)

W = 72
print(f"\n{'=' * W}")
print(f"  Retriever Comparison — Alzheimer's RAG")
print(f"{'=' * W}")
print(f"{'Metric':<30} {'BioBERT':>10} {'TF-IDF':>10} {'Delta':>10}")
print(f"{'-' * W}")

metrics = [
    ("Mean Precision@5",  "mean_precision_at_5"),
    ("Mean MRR",          "mean_mrr"),
    ("Hit Rate",          "hit_rate"),
    ("Mean Faithfulness", "mean_faithfulness"),
    ("Completeness Rate", "completeness_rate"),
]

for label, key in metrics:
    bb  = data["biobert"]["aggregate"][key]
    tf  = data["tfidf"]["aggregate"][key]
    delta = tf - bb
    sign  = "+" if delta >= 0 else ""
    print(f"  {label:<28} {bb:>10.3f} {tf:>10.3f} {sign}{delta:>9.3f}")

print(f"{'=' * W}\n")
EOF

test:
	$(PYTHON) -m pytest tests/ -v
