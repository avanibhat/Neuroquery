import logging
import os
from huggingface_hub import InferenceClient
from config import GROQ_API_KEY, GROQ_MODEL

log = logging.getLogger(__name__)

_client = None

HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"

SYSTEM_PROMPT = """You are an expert biomedical research assistant specialising in \
Alzheimer's Disease (AD). Your knowledge spans molecular mechanisms, genetics, \
biomarkers, clinical trials, diagnostics, and therapeutic strategies related to AD.

When answering:
- Ground every claim in the provided context blocks. Do not fabricate citations or facts.
- If the context is insufficient to answer fully, say so explicitly.
- Use precise scientific language appropriate for a research audience.
- When multiple sources agree or conflict, note it.
- Structure longer answers with clear headings or bullet points where helpful."""


def _get_client() -> InferenceClient:
    global _client
    if _client is None:
        hf_token = os.getenv("HF_TOKEN")
        _client = InferenceClient(
            model=HF_MODEL,
            token=hf_token,
        )
        log.info("HuggingFace InferenceClient initialised (model: %s).", HF_MODEL)
    return _client


def generate_response(query: str, context_chunks: list[dict]) -> str:
    if not context_chunks:
        return "No relevant documents were found. Please ingest research documents first."

    context_section = "\n\n".join(
        f"[{i + 1}] Source: {c['source']}\n{c['text']}"
        for i, c in enumerate(context_chunks)
    )

    prompt = f"""<s>[INST] {SYSTEM_PROMPT}

The following context blocks were retrieved from Alzheimer's research literature. Use them to answer the question below.

--- CONTEXT ---
{context_section}
--- END CONTEXT ---

Question: {query} [/INST]"""

    log.info("Calling HF Inference API (%s) with %d context chunks.", HF_MODEL, len(context_chunks))
    client = _get_client()
    response = client.text_generation(
        prompt,
        max_new_tokens=1024,
        temperature=0.3,
        repetition_penalty=1.1,
        do_sample=True,
    )
    log.info("Response received (%d chars).", len(response))
    return response
