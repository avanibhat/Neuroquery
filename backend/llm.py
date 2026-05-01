"""
llm.py — Generate answers using Groq (free tier) as a biomedical Alzheimer's research assistant.
"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

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
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env")
        _client = Groq(api_key=api_key)
    return _client


def generate_response(query: str, context_chunks: list[dict]) -> str:
    """
    Generate a grounded answer using Groq (Llama 3.3 70B) with retrieved context.

    Args:
        query:          The user's research question.
        context_chunks: List of {"text": str, "source": str} from the retriever.

    Returns:
        The assistant's text response.
    """
    if not context_chunks:
        return (
            "No relevant documents were found in the knowledge base to answer "
            "your question. Please ingest research documents first."
        )

    context_section = "\n\n".join(
        f"[{i + 1}] Source: {chunk['source']}\n{chunk['text']}"
        for i, chunk in enumerate(context_chunks)
    )

    user_message = f"""The following context blocks were retrieved from Alzheimer's \
research literature. Use them to answer the question below.

--- CONTEXT ---
{context_section}
--- END CONTEXT ---

Question: {query}"""

    client = _get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content
