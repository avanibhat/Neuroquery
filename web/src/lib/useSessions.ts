import { useCallback, useEffect, useState } from "react";
import type { Message, Session } from "../types";

const STORAGE_KEY = "nq_sessions_v2";
const MAX_SESSIONS = 30;

export const newId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

function load(): Session[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return []; // private mode, corrupted data, storage disabled
  }
}

function save(sessions: Session[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.slice(0, MAX_SESSIONS)));
  } catch {
    /* quota exceeded or storage disabled: keep working in memory */
  }
}

export function titleFrom(query: string): string {
  const t = query.trim().replace(/\s+/g, " ");
  return t.length > 48 ? `${t.slice(0, 45)}…` : t;
}

/** Conversation history, newest first, persisted per browser. */
export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>(load);
  const [activeId, setActiveId] = useState<string | null>(() => sessions[0]?.id ?? null);

  useEffect(() => save(sessions), [sessions]);

  const active = sessions.find((s) => s.id === activeId) ?? null;

  const startNew = useCallback(() => setActiveId(null), []);

  /** Append a message, creating the session on the first message. Returns the session id. */
  const append = useCallback(
    (sessionId: string | null, message: Message): string => {
      const id = sessionId ?? newId();
      setSessions((prev) => {
        const existing = prev.find((s) => s.id === id);
        const updated: Session = existing
          ? { ...existing, messages: [...existing.messages, message], updatedAt: Date.now() }
          : {
              id,
              title: message.role === "user" ? titleFrom(message.text) : "New conversation",
              messages: [message],
              updatedAt: Date.now(),
            };
        return [updated, ...prev.filter((s) => s.id !== id)];
      });
      setActiveId(id);
      return id;
    },
    [],
  );

  const removeMessage = useCallback((sessionId: string, messageId: string) => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === sessionId ? { ...s, messages: s.messages.filter((m) => m.id !== messageId) } : s,
      ),
    );
  }, []);

  const remove = useCallback(
    (sessionId: string) => {
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (sessionId === activeId) setActiveId(null);
    },
    [activeId],
  );

  return { sessions, active, activeId, setActiveId, startNew, append, removeMessage, remove };
}
