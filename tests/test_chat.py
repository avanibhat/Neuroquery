import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

FAKE_CHUNKS = [
    {"text": "Plasma p-tau217 tracks amyloid pathology.", "source": "pubmed:111"},
    {"text": "APOE4 is the strongest genetic risk factor.", "source": "pubmed:222"},
    {"text": "A second chunk from the same abstract.", "source": "pubmed:111"},
    {"text": "Notes from a local review article.", "source": "pdf:review.pdf"},
]


@pytest.fixture(scope="module")
def client():
    with patch("main._get_collection") as mock_col:
        mock_col.return_value = MagicMock(count=lambda: 100)
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture
def fake_pipeline():
    with patch("main.retrieve", return_value=FAKE_CHUNKS), \
         patch("main.generate_response", return_value="Grounded answer [1]."), \
         patch("main._save_history"):
        yield


def test_chat_returns_answer_and_passages(client, fake_pipeline):
    res = client.post("/chat", json={"query": "What are early blood biomarkers?"})
    assert res.status_code == 200
    data = res.json()
    assert data["response"] == "Grounded answer [1]."
    assert [p["rank"] for p in data["passages"]] == [1, 2, 3, 4]
    assert data["passages"][0]["text"].startswith("Plasma p-tau217")


def test_chat_sources_are_unique_and_ordered(client, fake_pipeline):
    data = client.post("/chat", json={"query": "APOE4?"}).json()
    assert data["sources"] == ["pubmed:111", "pubmed:222", "pdf:review.pdf"]


def test_chat_links_pubmed_sources_only(client, fake_pipeline):
    passages = client.post("/chat", json={"query": "APOE4?"}).json()["passages"]
    assert passages[0]["url"] == "https://pubmed.ncbi.nlm.nih.gov/111/"
    assert passages[3]["url"] is None


def test_chat_reports_timing(client, fake_pipeline):
    timing = client.post("/chat", json={"query": "APOE4?"}).json()["timing"]
    assert timing["retrieval_ms"] >= 0
    assert timing["generation_ms"] >= 0


@pytest.mark.parametrize("query", ["", "   "])
def test_chat_rejects_empty_query(client, fake_pipeline, query):
    assert client.post("/chat", json={"query": query}).status_code == 422


def test_chat_returns_500_when_llm_fails(client):
    with patch("main.retrieve", return_value=FAKE_CHUNKS), \
         patch("main.generate_response", side_effect=RuntimeError("Groq down")):
        res = client.post("/chat", json={"query": "APOE4?"})
    assert res.status_code == 500
    assert "Groq down" in res.json()["detail"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_eval_endpoint_shape(client):
    data = client.get("/eval").json()
    assert "retrievers" in data
    for scores in data["retrievers"].values():
        assert "mean_precision_at_5" in scores
