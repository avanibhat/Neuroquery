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

Full scores in [`eval_results_biobert.json`](eval_results_biobert.json) and [`eval_results_tfidf.json`](eval_results_tfidf.json).

| Metric | BioBERT | TF-IDF | Delta |
|--------|---------|--------|-------|
| Mean Precision@5 | 0.26 | 0.27 | +0.01 |
| Mean MRR | 0.48 | 0.53 | +0.05 |
| Hit Rate | 0.70 | 0.65 | -0.05 |
| Mean Faithfulness | 0.33 | 0.46 | +0.13 |
| Completeness Rate | 0.90 | 0.90 | 0.00 |

#### Per-question breakdown

| # | Question | BB P@5 | BB MRR | BB Hit | TF P@5 | TF MRR | TF Hit |
|---|----------|--------|--------|--------|--------|--------|--------|
| 1 | Earliest blood-based biomarkers? | 0.00 | 0.00 | N | 0.20 | 0.25 | Y |
| 2 | pTau-217 as biomarker? | 0.20 | 0.33 | Y | 0.00 | 0.00 | N |
| 3 | Aβ 42/40 ratio in diagnosis? | 0.00 | 0.00 | N | 0.00 | 0.00 | N |
| 4 | CSF biomarkers for diagnosis? | 0.20 | 0.25 | Y | 0.20 | 0.20 | Y |
| 5 | APOE4 allele and risk? | 0.40 | 1.00 | Y | 0.60 | 1.00 | Y |
| 6 | Early-onset familial AD genes? | 0.20 | 0.33 | Y | 0.00 | 0.00 | N |
| 7 | TREM2 variant effect? | 0.00 | 0.00 | N | 0.00 | 0.00 | N |
| 8 | APP gene mutation significance? | 0.00 | 0.00 | N | 0.60 | 1.00 | Y |
| 9 | Lecanemab mechanism? | 0.00 | 0.00 | N | 0.00 | 0.00 | N |
| 10 | Tau-targeting therapies? | 0.20 | 1.00 | Y | 0.20 | 1.00 | Y |
| 11 | FDA-approved treatments? | 0.20 | 0.33 | Y | 0.00 | 0.00 | N |
| 12 | Anti-amyloid immunotherapy? | 0.60 | 0.50 | Y | 0.40 | 1.00 | Y |
| 13 | Aβ accumulation → neurodegeneration? | 0.40 | 1.00 | Y | 0.20 | 1.00 | Y |
| 14 | Amyloid cascade hypothesis? | 0.40 | 1.00 | Y | 0.60 | 1.00 | Y |
| 15 | Neurofibrillary tangle formation? | 0.20 | 1.00 | Y | 0.40 | 1.00 | Y |
| 16 | Neuroinflammation in AD? | 0.80 | 1.00 | Y | 0.60 | 1.00 | Y |
| 17 | PET imaging in diagnosis? | 0.40 | 0.50 | Y | 0.80 | 1.00 | Y |
| 18 | Cognitive assessments for severity? | 0.40 | 0.33 | Y | 0.00 | 0.00 | N |
| 19 | Structural MRI in diagnosis? | 0.60 | 1.00 | Y | 0.40 | 1.00 | Y |
| 20 | Preclinical AD diagnostic criteria? | 0.00 | 0.00 | N | 0.20 | 0.20 | Y |

```bash
make eval          # saves eval_results_biobert.json
make eval-tfidf    # saves eval_results_tfidf.json
make eval-compare  # prints side-by-side delta table
```

---

## Observations

The 500-abstract corpus improves both retrievers substantially over the 100-abstract
baseline (Precision@5 roughly 0.16 → 0.26-0.27). The two retrievers land close together
on aggregate, but differ meaningfully on individual questions:

**BioBERT outperforms TF-IDF** on questions phrased with synonyms or indirect language
not present verbatim in the abstracts (Q2 "pTau-217 as biomarker", Q6 "early-onset
familial AD genes", Q11 "FDA-approved treatments", Q18 "cognitive assessments").
These are cases where dense semantic embeddings capture meaning that exact keyword
matching misses.

**TF-IDF outperforms BioBERT** on questions containing rare, distinctive terms that
appear verbatim in the corpus (Q1 "blood-based biomarkers", Q8 "APP gene mutation",
Q17 "PET imaging"). Sparse retrieval excels when the question's vocabulary closely
matches the source text.

**Neither retriever handles well:** Q3 (amyloid-beta 42/40 ratio), Q7 (TREM2 variant),
and Q9 (lecanemab mechanism) score zero hits on both retrievers — likely a corpus gap
where the 500 abstracts don't contain enough detail on these specific subtopics.

Faithfulness is notably higher for TF-IDF (0.46 vs 0.33) despite similar precision,
suggesting that when TF-IDF retrieves a relevant chunk it tends to be more directly
on-topic (lower noise), giving the LLM cleaner context to ground its answer in.

### Complementarity

The two retrievers are complementary in practice, not just in theory: this data shows
each one wins on different question types. A production system could use a
**hybrid retrieval** strategy — rank by a weighted sum of BioBERT cosine similarity
and TF-IDF cosine similarity, or use Reciprocal Rank Fusion (RRF) — to capture both
semantic and keyword-exact matches.

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
