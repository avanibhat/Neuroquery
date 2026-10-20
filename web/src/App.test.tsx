import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App";

const CHAT_RESPONSE = {
  response: "Plasma p-tau217 is an early marker [1]. APOE4 is unrelated here.",
  sources: ["pubmed:111", "pubmed:222"],
  passages: [
    { rank: 1, source: "pubmed:111", text: "Plasma p-tau217 rises early.", url: "https://pubmed.ncbi.nlm.nih.gov/111/" },
    { rank: 2, source: "pubmed:222", text: "An unrelated passage.", url: "https://pubmed.ncbi.nlm.nih.gov/222/" },
  ],
  timing: { retrieval_ms: 42, generation_ms: 1800 },
};

function mockFetch(chat: () => Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/stats")) {
        return Promise.resolve(new Response(JSON.stringify({ total_chunks: 1234, collection: "x" })));
      }
      return Promise.resolve(chat());
    }),
  );
}

beforeEach(() => {
  localStorage.clear();
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => vi.unstubAllGlobals());

async function ask(question: string) {
  render(<App />);
  fireEvent.change(screen.getByLabelText("Research question"), { target: { value: question } });
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));
}

it("shows the answer with its evidence and marks which passages were cited", async () => {
  mockFetch(() => new Response(JSON.stringify(CHAT_RESPONSE)));
  await ask("Early biomarkers?");

  expect(await screen.findByText(/is an early marker/)).toBeInTheDocument();
  expect(screen.getByText("2 passages retrieved · 1 cited in the answer")).toBeInTheDocument();
  expect(screen.getByText("cited")).toBeInTheDocument();
  expect(screen.getByText("not cited")).toBeInTheDocument();
  expect(screen.getByText(`${(1234).toLocaleString()} indexed chunks`)).toBeInTheDocument();
});

it("highlights the passage when a citation is clicked", async () => {
  mockFetch(() => new Response(JSON.stringify(CHAT_RESPONSE)));
  await ask("Early biomarkers?");

  fireEvent.click(await screen.findByTitle("Show passage 1"));
  const passage = screen.getByText("Plasma p-tau217 rises early.").closest("li");
  expect(passage).toHaveClass("highlight");
});

it("shows the server error and lets the user retry", async () => {
  mockFetch(() => new Response(JSON.stringify({ detail: "GROQ_API_KEY is not set" }), { status: 500 }));
  await ask("Early biomarkers?");

  expect(await screen.findByRole("alert")).toHaveTextContent("GROQ_API_KEY is not set");
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});

it("keeps the conversation in the sidebar", async () => {
  mockFetch(() => new Response(JSON.stringify(CHAT_RESPONSE)));
  await ask("Early biomarkers?");
  await waitFor(() => expect(screen.getByTitle("Early biomarkers?")).toBeInTheDocument());
});
