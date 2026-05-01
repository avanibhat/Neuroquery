import logging
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

log = logging.getLogger(__name__)

_client = None

SYSTEM_PROMPT = """You are an expert biomedical research assistant specialising in \
Alzheimer's Disease (AD). Your knowledge spans molecular mechanisms, genetics, \
biomarkers, clinical trials, diagnostics, and therapeutic strategies related to AD.

When answering:
- Ground every claim in the provided context blocks. Do not fabricate citations or facts.
- If the context is insufficient to answer fully, say so explicitly.
- Use precise scientific language appropriate for a research audience.
- When multiple sources agree or conflict, note it.
- Structure longer answers with clear headings or bullet points where helpful."""


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in .env")
        _client = Groq(api_key=GROQ_API_KEY, timeout=30.0, max_retries=0)
        log.info("Groq client initialised (model: %s).", GROQ_MODEL)
    return _client


def generate_response(query: str, context_chunks: list[dict]) -> str:
    if not context_chunks:
        return "No relevant documents were found. Please ingest research documents first."

    context_section = "\n\n".join(
        f"[{i + 1}] Source: {c['source']}\n{c['text']}"
        for i, c in enumerate(context_chunks)
    )
    user_message = f"""Context blocks retrieved from Alzheimer's research literature:

--- CONTEXT ---
{context_section}
--- END CONTEXT ---

Question: {query}"""

    log.info("Calling Groq (%s) with %d context chunks.", GROQ_MODEL, len(context_chunks))
    response = _get_client().chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    )
    answer = response.choices[0].message.content
    log.info("Groq response received (%d chars).", len(answer))
    return answer
