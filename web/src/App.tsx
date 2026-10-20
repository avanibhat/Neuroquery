import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AnswerMessage from "./components/AnswerMessage";
import Composer from "./components/Composer";
import EvalCard from "./components/EvalCard";
import EvidencePanel from "./components/EvidencePanel";
import Sidebar from "./components/Sidebar";
import { api } from "./lib/api";
import { citedPassages } from "./lib/citations";
import { newId, useSessions } from "./lib/useSessions";
import type { Message, Stats } from "./types";

const SUGGESTIONS = [
  "What are the earliest blood-based biomarkers of Alzheimer's?",
  "How does APOE4 affect Alzheimer's risk?",
  "What is the mechanism of action of lecanemab?",
  "What role does neuroinflammation play in disease progression?",
];

type AssistantMessage = Extract<Message, { role: "assistant" }>;

export default function App() {
  const { sessions, active, activeId, setActiveId, startNew, append, removeMessage, remove } =
    useSessions();

  const [busy, setBusy] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const [evalOpen, setEvalOpen] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false); // mobile drawer
  const [prefill, setPrefill] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.stats().then(setStats).catch(() => setStats(null));
  }, []);

  const messages = active?.messages ?? [];

  // The evidence panel follows the selected answer, or the latest one.
  const selected = useMemo<AssistantMessage | null>(() => {
    const answers = messages.filter((m): m is AssistantMessage => m.role === "assistant");
    return answers.find((m) => m.id === selectedId) ?? answers[answers.length - 1] ?? null;
  }, [messages, selectedId]);

  const cited = useMemo(
    () => (selected ? citedPassages(selected.text, selected.passages.length) : new Set<number>()),
    [selected],
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, busy]);

  const send = useCallback(
    async (query: string) => {
      const sessionId = append(activeId, { id: newId(), role: "user", text: query });
      setBusy(true);
      setHighlighted(null);
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await api.chat(query, controller.signal);
        const answer: AssistantMessage = {
          id: newId(),
          role: "assistant",
          text: res.response,
          passages: res.passages ?? [],
          timing: res.timing ?? null,
        };
        append(sessionId, answer);
        setSelectedId(answer.id);
      } catch (err) {
        // controller is only aborted when the user presses Stop; timeouts and
        // server errors still get an error bubble with a retry button.
        if (!controller.signal.aborted) {
          append(sessionId, {
            id: newId(),
            role: "error",
            text: err instanceof Error ? err.message : "Something went wrong.",
            retryQuery: query,
          });
        }
      } finally {
        setBusy(false);
        abortRef.current = null;
      }
    },
    [activeId, append],
  );

  const retry = (sessionId: string, msgId: string, query: string) => {
    removeMessage(sessionId, msgId);
    void send(query);
  };

  const showCitation = (answerId: string, rank: number) => {
    setSelectedId(answerId);
    setHighlighted(rank);
    setEvidenceOpen(true);
  };

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={(id) => {
          setActiveId(id);
          setSelectedId(null);
          setHighlighted(null);
        }}
        onNew={() => {
          startNew();
          setSelectedId(null);
          setHighlighted(null);
        }}
        onDelete={remove}
      />

      <main className="main">
        <header className="topbar">
          <div className="brand">
            <div className="logo" aria-hidden>
              NQ
            </div>
            <div>
              <h1>NeuroQuery</h1>
              <p>Alzheimer's research assistant · answers grounded in PubMed</p>
            </div>
          </div>
          <div className="topbar-actions">
            {stats && <span className="badge">{stats.total_chunks.toLocaleString()} indexed chunks</span>}
            <button type="button" className="outline-btn" onClick={() => setEvalOpen(true)}>
              Reliability
            </button>
            {selected && (
              <button
                type="button"
                className="outline-btn evidence-toggle"
                onClick={() => setEvidenceOpen((o) => !o)}
              >
                Evidence
              </button>
            )}
          </div>
        </header>

        <section className="thread" aria-live="polite">
          {messages.length === 0 ? (
            <div className="welcome">
              <h2>Ask a research question</h2>
              <p>
                Every answer cites the PubMed abstracts it was built from. Click a citation number to
                see the exact passage.
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} type="button" className="suggestion" onClick={() => void send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => {
              if (m.role === "user") {
                return (
                  <article key={m.id} className="msg user">
                    <div className="bubble">{m.text}</div>
                    <button type="button" className="link-btn" onClick={() => setPrefill(m.text)}>
                      Edit
                    </button>
                  </article>
                );
              }
              if (m.role === "error") {
                return (
                  <article key={m.id} className="msg error" role="alert">
                    <div className="bubble">{m.text}</div>
                    <button
                      type="button"
                      className="small-btn"
                      disabled={busy}
                      onClick={() => active && retry(active.id, m.id, m.retryQuery)}
                    >
                      Retry
                    </button>
                  </article>
                );
              }
              return (
                <AnswerMessage
                  key={m.id}
                  text={m.text}
                  passages={m.passages}
                  timing={m.timing}
                  selected={selected?.id === m.id}
                  onSelect={() => setSelectedId(m.id)}
                  onCite={(rank) => showCitation(m.id, rank)}
                />
              );
            })
          )}
          {busy && (
            <div className="msg assistant pending" aria-label="Generating answer">
              <div className="msg-label">NeuroQuery</div>
              <div className="bubble">
                <span className="dots">
                  <i />
                  <i />
                  <i />
                </span>
                Searching the literature and writing an answer…
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </section>

        <Composer busy={busy} onSend={(q) => void send(q)} onCancel={() => abortRef.current?.abort()} prefill={prefill} />
      </main>

      <div className={`evidence-wrap ${evidenceOpen ? "open" : ""}`}>
        <EvidencePanel
          passages={selected?.passages ?? []}
          cited={cited}
          highlighted={highlighted}
          onClose={() => setEvidenceOpen(false)}
        />
      </div>

      {evalOpen && <EvalCard onClose={() => setEvalOpen(false)} />}
    </div>
  );
}
