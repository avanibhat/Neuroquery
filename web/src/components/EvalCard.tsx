import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { EvalResponse, EvalScores } from "../types";

const ROWS: { key: keyof EvalScores; label: string; hint: string }[] = [
  { key: "mean_precision_at_5", label: "Precision@5", hint: "Share of the top 5 passages judged relevant" },
  { key: "hit_rate", label: "Hit rate", hint: "Questions with at least one relevant passage" },
  { key: "mean_faithfulness", label: "Faithfulness", hint: "How well answers stick to the retrieved text" },
  { key: "completeness_rate", label: "Completeness", hint: "Answers that address the question" },
];

const pct = (v: number) => `${Math.round(v * 100)}%`;

/** Reports the offline LLM-as-judge scores so users know how far to trust answers. */
export default function EvalCard({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<EvalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.eval().then(setData).catch((e: Error) => setError(e.message));
  }, []);

  const bb = data?.retrievers.biobert;
  const tf = data?.retrievers.tfidf;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="eval-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-head">
          <h2 id="eval-title">How reliable are the answers?</h2>
          <button type="button" className="ghost-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>

        {error && <p className="muted">Could not load evaluation results: {error}</p>}
        {!data && !error && <p className="muted">Loading…</p>}
        {data && !bb && !tf && (
          <p className="muted">No evaluation results found. Run <code>make eval</code> first.</p>
        )}

        {(bb || tf) && (
          <>
            <p className="muted">
              Scored by an LLM judge on {bb?.questions_evaluated ?? tf?.questions_evaluated} research
              questions across biomarkers, genetics, therapeutics, mechanisms and diagnostics.
            </p>
            <table className="eval-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>BioBERT</th>
                  <th>TF-IDF</th>
                </tr>
              </thead>
              <tbody>
                {ROWS.map((r) => (
                  <tr key={r.key}>
                    <td title={r.hint}>
                      {r.label}
                      <span className="hint">{r.hint}</span>
                    </td>
                    <td>{bb ? pct(bb[r.key]) : "–"}</td>
                    <td>{tf ? pct(tf[r.key]) : "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted small">
              Faithfulness is the weak spot, which is why every answer shows its passages. Check the
              evidence before relying on a claim.
            </p>
          </>
        )}
      </section>
    </div>
  );
}
