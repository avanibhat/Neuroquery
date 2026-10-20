import { useEffect, useRef } from "react";
import type { Passage } from "../types";
import { formatSource } from "../lib/citations";

interface Props {
  passages: Passage[];
  cited: Set<number>;
  highlighted: number | null;
  onClose?: () => void;
}

/**
 * Shows every chunk the retriever handed to the LLM, so the reader can check
 * which claims are backed by which abstract — and which passages went unused.
 */
export default function EvidencePanel({ passages, cited, highlighted, onClose }: Props) {
  const refs = useRef(new Map<number, HTMLLIElement>());

  useEffect(() => {
    if (highlighted == null) return;
    refs.current.get(highlighted)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [highlighted]);

  const usedCount = passages.filter((p) => cited.has(p.rank)).length;

  return (
    <aside className="evidence" aria-label="Retrieved evidence">
      <header className="evidence-head">
        <div>
          <h2>Evidence</h2>
          <p>
            {passages.length === 0
              ? "Ask a question to see the passages behind the answer."
              : `${passages.length} passages retrieved · ${usedCount} cited in the answer`}
          </p>
        </div>
        {onClose && (
          <button type="button" className="ghost-btn" onClick={onClose} aria-label="Close evidence">
            ✕
          </button>
        )}
      </header>

      <ol className="passages">
        {passages.map((p) => {
          const isCited = cited.has(p.rank);
          return (
            <li
              key={p.rank}
              ref={(el) => {
                if (el) refs.current.set(p.rank, el);
                else refs.current.delete(p.rank);
              }}
              className={`passage ${isCited ? "cited" : "unused"} ${
                highlighted === p.rank ? "highlight" : ""
              }`}
            >
              <div className="passage-head">
                <span className="rank">{p.rank}</span>
                {p.url ? (
                  <a href={p.url} target="_blank" rel="noreferrer">
                    {formatSource(p.source)} ↗
                  </a>
                ) : (
                  <span>{formatSource(p.source)}</span>
                )}
                <span className={`tag ${isCited ? "tag-cited" : "tag-unused"}`}>
                  {isCited ? "cited" : "not cited"}
                </span>
              </div>
              <p className="passage-text">{p.text}</p>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
