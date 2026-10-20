import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

const MAX_LEN = 1000;

interface Props {
  busy: boolean;
  onSend: (query: string) => void;
  onCancel: () => void;
  prefill: string | null;
}

export default function Composer({ busy, onSend, onCancel, prefill }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (prefill != null) {
      setValue(prefill);
      ref.current?.focus();
    }
  }, [prefill]);

  // Grow with content up to a limit
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const trimmed = value.trim();
  const canSend = !busy && trimmed.length > 0 && value.length <= MAX_LEN;

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    if (!canSend) return;
    onSend(trimmed);
    setValue("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask about biomarkers, genetics, therapies…"
        rows={1}
        aria-label="Research question"
      />
      <div className="composer-side">
        {value.length > MAX_LEN * 0.8 && (
          <span className={`counter ${value.length > MAX_LEN ? "over" : ""}`}>
            {value.length}/{MAX_LEN}
          </span>
        )}
        {busy ? (
          <button type="button" className="send-btn stop" onClick={onCancel}>
            Stop
          </button>
        ) : (
          <button type="submit" className="send-btn" disabled={!canSend}>
            Ask
          </button>
        )}
      </div>
    </form>
  );
}
