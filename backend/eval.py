"""
eval.py — Evaluation module for the Alzheimer's RAG system.

Measures:
  Precision@5   — fraction of retrieved chunks judged relevant by the LLM
  MRR           — Mean Reciprocal Rank of first relevant chunk
  Hit Rate      — fraction of questions with at least one relevant chunk
  Faithfulness  — 0-1 score: how grounded is the answer in retrieved context
  Completeness  — binary: does the answer appropriately address the question?

Usage:
    python backend/eval.py                          # BioBERT, full eval
    python backend/eval.py --retriever tfidf        # TF-IDF, full eval
    python backend/eval.py --dry-run                # 3 questions, quick test
    python backend/eval.py --resume                 # skip completed questions
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from statistics import mean

import groq as groq_module

sys.path.insert(0, str(Path(__file__).parent))

from retriever import retrieve, retrieve_tfidf
from llm import generate_response, _get_client
from config import GROQ_MODEL

QUESTIONS = [
    # Biomarkers
    "What are the earliest blood-based biomarkers for Alzheimer's disease?",
    "How does phosphorylated tau 217 serve as a biomarker for Alzheimer's disease?",
    "What is the significance of the amyloid-beta 42/40 ratio in diagnosing Alzheimer's disease?",
    "Which cerebrospinal fluid biomarkers are used to diagnose Alzheimer's disease?",
    # Genetics
    "What is the role of the APOE4 allele in Alzheimer's disease risk?",
    "Which genes are associated with early-onset familial Alzheimer's disease?",
    "How does the TREM2 gene variant affect Alzheimer's disease risk?",
    "What is the significance of the APP gene mutation in Alzheimer's disease?",
    # Therapeutics
    "What is the mechanism of action of lecanemab in treating Alzheimer's disease?",
    "How do tau-targeting therapies work in Alzheimer's disease treatment?",
    "What are the current FDA-approved treatments for Alzheimer's disease?",
    "What is the role of anti-amyloid immunotherapy in Alzheimer's disease?",
    # Mechanisms
    "How does amyloid-beta accumulation lead to neurodegeneration in Alzheimer's disease?",
    "What is the amyloid cascade hypothesis in Alzheimer's disease?",
    "How do neurofibrillary tangles form and contribute to Alzheimer's disease?",
    "What is the role of neuroinflammation in Alzheimer's disease progression?",
    # Diagnostics
    "How is PET imaging used in the diagnosis of Alzheimer's disease?",
    "What cognitive assessments are used to evaluate Alzheimer's disease severity?",
    "How does structural MRI help in diagnosing Alzheimer's disease?",
    "What are the diagnostic criteria for preclinical Alzheimer's disease?",
]


# ── Output paths ─────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent

def output_file(retriever: str) -> Path:
    return ROOT / f"eval_results_{retriever}.json"


# ── Retry logic ──────────────────────────────────────────────────────────────

def _parse_retry_after(error: Exception) -> float:
    m = re.search(r"retry after (\d+(?:\.\d+)?)", str(error), re.IGNORECASE)
    return float(m.group(1)) + 1.0 if m else 0.0


def _call_with_retry(fn, max_retries: int = 15):
    delay = 5.0
    for attempt in range(max_retries):
        try:
            return fn()
        except groq_module.RateLimitError as e:
            # Prefer the server's own "retry after N seconds" hint; fall back to backoff.
            hint = _parse_retry_after(e)
            wait = max(hint, delay)
            print(f"\n  [rate limit] waiting {wait:.0f}s (retry {attempt+1}/{max_retries})...")
            time.sleep(wait)
            delay = min(delay * 2, 300)
        except groq_module.APIConnectionError:
            if attempt == max_retries - 1:
                raise
            print(f"\n  [connection error] retrying in {delay:.0f}s...")
            time.sleep(delay)
            delay = min(delay * 2, 300)
    raise RuntimeError(f"Failed after {max_retries} retries.")


# ── LLM judge helpers ────────────────────────────────────────────────────────

def _judge(prompt: str, client) -> str:
    def call():
        r = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=50,
            temperature=0.0,
            messages=[
                {"role": "system",
                 "content": "You are an objective evaluator. Follow instructions exactly and respond only as instructed."},
                {"role": "user", "content": prompt},
            ],
        )
        return r.choices[0].message.content.strip()
    return _call_with_retry(call)


def judge_relevance(question: str, chunk: str, client) -> bool:
    prompt = (
        f"Question: {question}\n\n"
        f"Chunk: {chunk[:500]}\n\n"
        "Is this chunk relevant to answering the question? Reply with exactly one word: YES or NO."
    )
    return _judge(prompt, client).upper().startswith("YES")


def judge_faithfulness(question: str, answer: str, chunks: list[dict], client) -> float:
    context = "\n\n".join(f"[{i+1}] {c['text'][:300]}" for i, c in enumerate(chunks))
    prompt = (
        f"Question: {question}\n\nRetrieved context:\n{context}\n\nAnswer: {answer[:600]}\n\n"
        "Rate faithfulness 0-10 (10=fully grounded, 0=unsupported claims). Reply with one integer."
    )
    raw = _judge(prompt, client)
    m   = re.search(r"\d+", raw)
    return round(min(int(m.group()), 10) / 10, 2) if m else 0.5


def judge_completeness(question: str, answer: str, client) -> bool:
    prompt = (
        f"Question: {question}\n\nAnswer: {answer[:600]}\n\n"
        "Does this answer appropriately address the question (substantive response or clear "
        "statement of insufficient context)? Reply with exactly one word: YES or NO."
    )
    return _judge(prompt, client).upper().startswith("YES")


# ── Retrieval metrics ────────────────────────────────────────────────────────

def compute_mrr(relevant: list[bool]) -> float:
    """Reciprocal rank of the first relevant chunk (1-indexed). 0 if none relevant."""
    for rank, is_rel in enumerate(relevant, 1):
        if is_rel:
            return round(1.0 / rank, 4)
    return 0.0


def compute_hit_rate(relevant: list[bool]) -> bool:
    return any(relevant)


# ── Per-question evaluation ──────────────────────────────────────────────────

def evaluate_question(
    q: str, idx: int, total: int, client, retriever_fn
) -> dict:
    print(f"  [{idx:>2}/{total}] {q[:68]}...")

    def get_answer():
        chunks = retriever_fn(q, n_results=5)
        answer = generate_response(q, chunks)
        return chunks, answer

    chunks, answer = _call_with_retry(get_answer)
    time.sleep(0.5)

    relevant = []
    for chunk in chunks:
        relevant.append(judge_relevance(q, chunk["text"], client))
        time.sleep(0.3)

    precision    = round(sum(relevant) / len(chunks), 3) if chunks else 0.0
    mrr          = compute_mrr(relevant)
    hit          = compute_hit_rate(relevant)
    faithfulness = judge_faithfulness(q, answer, chunks, client)
    time.sleep(0.3)
    complete     = judge_completeness(q, answer, client)
    time.sleep(0.3)

    print(
        f"       P@5={precision:.2f}  MRR={mrr:.2f}  "
        f"Hit={'Y' if hit else 'N'}  "
        f"Faith={faithfulness:.2f}  "
        f"Complete={'Yes' if complete else 'No'}"
    )

    return {
        "id":              idx,
        "question":        q,
        "precision_at_5":  precision,
        "mrr":             mrr,
        "hit":             hit,
        "relevant_chunks": sum(relevant),
        "faithfulness":    faithfulness,
        "complete":        complete,
        "answer_excerpt":  answer[:300].replace("\n", " "),
    }


# ── Resume helpers ───────────────────────────────────────────────────────────

def load_completed(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f).get("questions", [])


def save_partial(path: Path, new_result: dict):
    existing = {r["id"]: r for r in load_completed(path)}
    existing[new_result["id"]] = new_result
    with open(path, "w") as f:
        json.dump({"questions": list(existing.values())}, f, indent=2)


# ── Summary table ────────────────────────────────────────────────────────────

def compute_aggregate(results: list[dict]) -> dict:
    return {
        "questions_evaluated": len(results),
        "mean_precision_at_5": round(mean(r["precision_at_5"] for r in results), 3),
        "mean_mrr":            round(mean(r["mrr"]            for r in results), 3),
        "hit_rate":            round(sum(r["hit"]             for r in results) / len(results), 3),
        "mean_faithfulness":   round(mean(r["faithfulness"]   for r in results), 3),
        "completeness_rate":   round(sum(r["complete"]        for r in results) / len(results), 3),
    }


def print_summary(results: list[dict], agg: dict, retriever: str):
    W = 82
    print(f"\n{'=' * W}")
    print(f"  Retriever: {retriever.upper()}")
    print(f"{'=' * W}")
    print(f"{'#':<4} {'Question':<43} {'P@5':>5} {'MRR':>5} {'Hit':>4} {'Faith':>6} {'Comp':>5}")
    print(f"{'-' * W}")
    for r in sorted(results, key=lambda x: x["id"]):
        q_short = r["question"][:41] + ".." if len(r["question"]) > 43 else r["question"]
        print(
            f"{r['id']:<4} {q_short:<43} "
            f"{r['precision_at_5']:>5.2f} "
            f"{r['mrr']:>5.2f} "
            f"{'Y' if r['hit'] else 'N':>4} "
            f"{r['faithfulness']:>6.2f} "
            f"{'Yes' if r['complete'] else 'No':>5}"
        )
    print(f"{'=' * W}")
    print(f"\nAggregate ({agg['questions_evaluated']} questions, retriever={retriever}):")
    print(f"  Mean Precision@5 : {agg['mean_precision_at_5']:.3f}")
    print(f"  Mean MRR         : {agg['mean_mrr']:.3f}")
    print(f"  Hit Rate         : {agg['hit_rate']:.1%}")
    print(f"  Mean Faithfulness: {agg['mean_faithfulness']:.3f}")
    print(f"  Completeness Rate: {agg['completeness_rate']:.1%}")
    print()


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Evaluate the Alzheimer's RAG pipeline.")
    parser.add_argument("--dry-run",  action="store_true", help="Run on 3 questions only.")
    parser.add_argument("--resume",   action="store_true", help="Skip already-completed questions.")
    parser.add_argument(
        "--retriever",
        choices=["biobert", "tfidf"],
        default="biobert",
        help="Retriever to evaluate (default: biobert).",
    )
    args = parser.parse_args()

    retriever_fn = retrieve if args.retriever == "biobert" else retrieve_tfidf
    out_path     = output_file(args.retriever)
    questions    = QUESTIONS[:3] if args.dry_run else QUESTIONS

    completed_ids: set[int] = set()
    prior_results: list[dict] = []
    if args.resume:
        prior_results = load_completed(out_path)
        completed_ids = {r["id"] for r in prior_results}
        if completed_ids:
            print(f"  Resuming - skipping {len(completed_ids)} completed questions.")

    remaining = [(i + 1, q) for i, q in enumerate(questions) if (i + 1) not in completed_ids]

    label = "DRY RUN" if args.dry_run else "FULL EVAL"
    print(f"\nAlzheimer's RAG Evaluation  [{label}]  retriever={args.retriever.upper()}")
    print(f"  To evaluate: {len(remaining)} questions  |  Already done: {len(completed_ids)}")
    print("  Metrics: P@5 | MRR | Hit Rate | Faithfulness | Completeness")
    if not args.dry_run:
        print("  Est. time: ~10-15 min  (auto-retry on Groq 429)")
    print()

    results = list(prior_results)

    if remaining:
        client = _get_client()
        for idx, q in remaining:
            result = evaluate_question(q, idx, len(questions), client, retriever_fn)
            results.append(result)
            save_partial(out_path, result)

    agg = compute_aggregate(results)
    with open(out_path, "w") as f:
        json.dump({"retriever": args.retriever, "aggregate": agg, "questions": results}, f, indent=2)
    print(f"\nResults saved -> {out_path}")

    print_summary(results, agg, args.retriever)


if __name__ == "__main__":
    main()
