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


def test_metrics():
    response = client.get("/metrics")

    assert response.status_code == 200


def test_chat_without_rag():
    response = client.post(
        "/chat",
        json={"query": "Hola"},
    )

    assert response.status_code == 503


def test_documents_upload_without_rag():
    response = client.post(
        "/documents",
        files={
            "file": (
                "test.txt",
                b"test content",
                "text/plain",
            )
        },
    )

    assert response.status_code == 503


def test_documents_list_without_rag():
    response = client.get("/documents")

    assert response.status_code == 503
