from fastapi.testclient import TestClient

from app.main import app


def test_empty_knowledge_search_is_safe() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/knowledge/search?q=x")
    assert response.status_code == 200
    assert response.json() == []
