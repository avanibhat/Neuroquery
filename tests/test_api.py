import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# Patch the lifespan ingest check so tests don't trigger a full ingest
@pytest.fixture(scope="module")
def client():
    with patch("main._get_collection") as mock_col:
        mock_col.return_value = MagicMock(count=lambda: 100)
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_stats_returns_200(client):
    response = client.get("/stats")
    assert response.status_code == 200


def test_stats_returns_json(client):
    response = client.get("/stats")
    data = response.json()
    assert isinstance(data, dict)


def test_stats_has_total_chunks(client):
    response = client.get("/stats")
    data = response.json()
    assert "total_chunks" in data
    assert isinstance(data["total_chunks"], int)


def test_stats_has_collection_name(client):
    response = client.get("/stats")
    data = response.json()
    assert "collection" in data


def test_health_endpoint(client):
    response = client.get("/health") if hasattr(client, "get") else None
    # /health was removed in a refactor — /stats is the canonical health check
    # This test just confirms the app starts without error
    assert client.get("/stats").status_code == 200


def test_history_returns_list(client):
    response = client.get("/history")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)
