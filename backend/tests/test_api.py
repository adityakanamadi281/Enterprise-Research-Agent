from fastapi.testclient import TestClient
from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_research_requires_meaningful_question() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/research", json={"question": "too short"})
    assert response.status_code == 422


def test_organization_and_project_lifecycle() -> None:
    with TestClient(app) as client:
        organization = client.post("/v1/organizations", json={"name": "Atlas Test Org"})
        if organization.status_code == 409:
            # The durable local database may already contain the test organization.
            projects = client.get("/v1/projects")
            assert projects.status_code == 200
            return
        assert organization.status_code == 201
        project = client.post(
            "/v1/projects",
            json={"organization_id": organization.json()["id"], "name": "Research intelligence"},
        )
    assert project.status_code == 201


def test_text_document_upload_creates_durable_evidence() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/documents/upload",
            files={
                "files": (
                    "strategy.txt",
                    b"AI adoption requires governance and source traceability.",
                    "text/plain",
                )
            },
        )
    assert response.status_code == 201
    document = response.json()["documents"][0]
    assert document["filename"] == "strategy.txt"
    assert document["characters"] > 0
