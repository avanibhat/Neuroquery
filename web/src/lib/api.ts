import type { ChatResponse, EvalResponse, Stats } from "../types";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Same origin in production; Vite proxies to FastAPI in development.
const BASE = "";

// BioBERT on CPU plus a 70B model can be slow, but never wait forever.
const CHAT_TIMEOUT_MS = 60_000;

async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = 15_000,
  signal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort("timeout"), timeoutMs);
  signal?.addEventListener("abort", () => controller.abort("cancelled"));

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init.headers },
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new ApiError(await readError(res), res.status);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (controller.signal.aborted) {
      throw new ApiError(
        controller.signal.reason === "cancelled"
          ? "Request cancelled."
          : "The server took too long to respond. Please try again.",
        null,
      );
    }
    throw new ApiError("Could not reach the server. Is the backend running?", null);
  } finally {
    clearTimeout(timer);
  }
}

/** FastAPI returns {detail: string} or {detail: [{msg}]} for validation errors. */
export async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    /* not JSON */
  }
  if (res.status === 429) return "Rate limit reached on the LLM provider. Wait a moment and retry.";
  return `Request failed (${res.status}).`;
}

export const api = {
  chat: (query: string, signal?: AbortSignal) =>
    request<ChatResponse>(
      "/chat",
      { method: "POST", body: JSON.stringify({ query }) },
      CHAT_TIMEOUT_MS,
      signal,
    ),
  stats: () => request<Stats>("/stats"),
  eval: () => request<EvalResponse>("/eval"),
};
