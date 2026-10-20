import type { Session } from "../types";

interface Props {
  sessions: Session[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export default function Sidebar({ sessions, activeId, onSelect, onNew, onDelete }: Props) {
  return (
    <nav className="sidebar" aria-label="Conversations">
      <div className="sidebar-head">
        <span>History</span>
        <button type="button" className="small-btn" onClick={onNew}>
          + New
        </button>
      </div>
      {sessions.length === 0 ? (
        <p className="sidebar-empty">Your conversations will appear here.</p>
      ) : (
        <ul className="session-list">
          {sessions.map((s) => (
            <li key={s.id} className={s.id === activeId ? "active" : ""}>
              <button type="button" className="session-btn" onClick={() => onSelect(s.id)} title={s.title}>
                {s.title}
              </button>
              <button
                type="button"
                className="delete-btn"
                onClick={() => onDelete(s.id)}
                aria-label={`Delete conversation ${s.title}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </nav>
  );
}
