from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ready():
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["phase"] == 1
    assert response.json()["ai_enabled"] is False


def test_metrics():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "rag_chat_requests_total" in response.text


def test_chat_not_available():
    response = client.post(
        "/chat",
        json={"query": "test"},
    )

    assert response.status_code == 503


def test_documents_upload_not_available():
    response = client.post(
        "/documents",
        files={
            "file": (
                "test.txt",
                b"test document",
                "text/plain",
            )
        },
    )

    assert response.status_code == 503


def test_documents_list_not_available():
    response = client.get("/documents")

    assert response.status_code == 503