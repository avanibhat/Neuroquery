import { memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import type { Passage, Timing } from "../types";
import { formatSource, linkCitations } from "../lib/citations";

interface Props {
  text: string;
  passages: Passage[];
  timing: Timing | null;
  selected: boolean;
  onSelect: () => void;
  onCite: (rank: number) => void;
}

function AnswerMessage({ text, passages, timing, selected, onSelect, onCite }: Props) {
  const markdown = useMemo(() => linkCitations(text, passages.length), [text, passages.length]);
  const sources = useMemo(
    () => [...new Map(passages.map((p) => [p.source, p])).values()],
    [passages],
  );

  return (
    <article className={`msg assistant ${selected ? "selected" : ""}`} onClick={onSelect}>
      <div className="msg-label">NeuroQuery</div>
      <div className="bubble markdown">
        <ReactMarkdown
          components={{
            a: ({ href, children }) => {
              const match = href?.match(/^#cite-(\d+)$/);
              if (match) {
                const rank = Number(match[1]);
                return (
                  <button
                    type="button"
                    className="cite"
                    title={`Show passage ${rank}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onCite(rank);
                    }}
                  >
                    {rank}
                  </button>
                );
              }
              return (
                <a href={href} target="_blank" rel="noreferrer">
                  {children}
                </a>
              );
            },
          }}
        >
          {markdown}
        </ReactMarkdown>
      </div>

      <footer className="msg-meta">
        {sources.length > 0 && (
          <span className="chips">
            {sources.map((p) =>
              p.url ? (
                <a key={p.source} className="chip" href={p.url} target="_blank" rel="noreferrer">
                  {formatSource(p.source)}
                </a>
              ) : (
                <span key={p.source} className="chip">
                  {formatSource(p.source)}
                </span>
              ),
            )}
          </span>
        )}
        {timing && (
          <span className="timing" title="Retrieval / generation time">
            {timing.retrieval_ms} ms retrieval · {(timing.generation_ms / 1000).toFixed(1)} s generation
          </span>
        )}
      </footer>
    </article>
  );
}

export default memo(AnswerMessage);
