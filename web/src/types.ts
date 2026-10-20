/** Mirrors the Pydantic models in backend/main.py. */

export interface Passage {
  rank: number;
  source: string;
  text: string;
  url: string | null;
}

export interface Timing {
  retrieval_ms: number;
  generation_ms: number;
}

export interface ChatResponse {
  response: string;
  sources: string[];
  passages: Passage[];
  timing: Timing | null;
}

export interface Stats {
  total_chunks: number;
  collection: string;
}

export interface EvalScores {
  questions_evaluated: number;
  mean_precision_at_5: number;
  mean_mrr: number;
  hit_rate: number;
  mean_faithfulness: number;
  completeness_rate: number;
}

export interface EvalResponse {
  retrievers: Partial<Record<"biobert" | "tfidf", EvalScores>>;
}

export type Message =
  | { id: string; role: "user"; text: string }
  | {
      id: string;
      role: "assistant";
      text: string;
      passages: Passage[];
      timing: Timing | null;
    }
  | { id: string; role: "error"; text: string; retryQuery: string };

export interface Session {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: number;
}
