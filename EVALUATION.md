# Evaluation Report — NeuroQuery

Evaluation of retrieval quality across 20 Alzheimer's Disease research questions,
comparing **BioBERT** (semantic/dense) vs **TF-IDF** (keyword/sparse) retrieval.
All metrics are assessed using Llama 3.3 70B (Groq) as judge.

---

## Metrics

| Metric | Description |
|--------|-------------|
| **Precision@5** | Fraction of 5 retrieved chunks judged relevant to the question |
| **MRR** | Mean Reciprocal Rank — 1/rank of first relevant chunk (1 = top result relevant) |
| **Hit Rate** | Fraction of questions with at least one relevant chunk in top 5 |
| **Faithfulness** | 0–1 score: how well the generated answer is grounded in retrieved context |
| **Completeness** | Fraction of answers that appropriately address the question |

---

## Results

### Baseline — BioBERT, 100 PubMed abstracts

Evaluated on 20 questions across 5 categories. Full scores in [`eval_results_100abstracts.json`](eval_results_100abstracts.json).

| Metric | Score |
|--------|-------|
| Mean Precision@5 | 0.16 |
| Mean Faithfulness | 0.53 |
| Completeness Rate | 0.90 |

#### Per-question breakdown

| # | Question | P@5 | Faith | Complete |
|---|----------|-----|-------|----------|
| 1 | Earliest blood-based biomarkers? | 0.60 | 0.80 | Yes |
| 2 | pTau-217 as biomarker? | 0.40 | 0.40 | Yes |
| 3 | Aβ 42/40 ratio in diagnosis? | 0.40 | 0.00 | Yes |
| 4 | CSF biomarkers for diagnosis? | 0.00 | 0.20 | Yes |
| 5 | APOE4 allele and risk? | 0.20 | 0.80 | Yes |
| 6 | Early-onset familial AD genes? | 0.00 | 0.80 | Yes |
| 7 | TREM2 variant effect? | 0.00 | 1.00 | Yes |
| 8 | APP gene mutation significance? | 0.00 | 0.80 | Yes |
| 9 | Lecanemab mechanism? | 0.20 | 0.80 | Yes |
| 10 | Tau-targeting therapies? | 0.00 | 0.40 | Yes |
| 11 | FDA-approved treatments? | 0.00 | 0.80 | Yes |
| 12 | Anti-amyloid immunotherapy? | 0.40 | 0.40 | Yes |
| 13 | Aβ accumulation → neurodegeneration? | 0.00 | 0.40 | No |
| 14 | Amyloid cascade hypothesis? | 0.20 | 0.80 | Yes |
| 15 | Neurofibrillary tangle formation? | 0.20 | 0.40 | No |
| 16 | Neuroinflammation in AD? | 0.20 | 0.00 | Yes |
| 17 | PET imaging in diagnosis? | 0.40 | 0.70 | Yes |
| 18 | Cognitive assessments for severity? | 0.00 | 0.80 | Yes |
| 19 | Structural MRI in diagnosis? | 0.00 | 0.00 | Yes |
| 20 | Preclinical AD diagnostic criteria? | 0.00 | 0.30 | Yes |

**Key observations:**
- Precision@5 is low (0.16) on 100 abstracts — most retrieved chunks are adjacent-topic rather than directly relevant. Expected to improve significantly with the 500-abstract corpus.
- Faithfulness is moderate (0.53) — the LLM generates grounded answers when good chunks are retrieved, but hedges when context is thin.
- Completeness is high (0.90) — the model almost always produces a substantive response (either an answer or a clear acknowledgement of limited context).

---

### BioBERT vs TF-IDF (500 abstracts)

*Run `make eval` then `make eval-tfidf` to populate.*

| Metric | BioBERT | TF-IDF | Delta |
|--------|---------|--------|-------|
| Mean Precision@5 | — | — | — |
| Mean MRR | — | — | — |
| Hit Rate | — | — | — |
| Mean Faithfulness | — | — | — |
| Completeness Rate | — | — | — |

```bash
make eval          # saves eval_results_biobert.json
make eval-tfidf    # saves eval_results_tfidf.json
make eval-compare  # prints side-by-side delta table
```

---

## Observations

### Expected Findings

**BioBERT** is expected to outperform TF-IDF on:
- Questions with semantic paraphrasing (e.g. "what makes APOE4 risky" vs "APOE4 risk mechanism")
- Questions using medical synonyms (e.g. "cognitive decline" ≈ "dementia progression")

**TF-IDF** is expected to outperform BioBERT on:
- Questions with rare proper nouns (e.g. drug names: "lecanemab", "donanemab")
- Questions targeting specific gene names or acronyms (e.g. "TREM2", "pTau-217")
- Situations where the exact terminology appears verbatim in abstracts

### Complementarity

The two retrievers are complementary by design. A production system could use a
**hybrid retrieval** strategy: rank by a weighted sum of BioBERT cosine similarity
and TF-IDF cosine similarity, or use Reciprocal Rank Fusion (RRF).

---

## Reproducibility

All evaluation results are deterministic at temperature 0.0 (judge LLM) and use
a fixed 20-question set. Re-running on a different ChromaDB snapshot (e.g. after
re-ingesting) may produce different scores if the underlying corpus changes.

```bash
# Reproduce from scratch
make ingest
make eval
make eval-tfidf
make eval-compare
```
