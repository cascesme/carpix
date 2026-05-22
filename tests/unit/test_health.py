"""Unit tests for health endpoint — API-03, API-05."""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from carpix_images.main import create_app


def test_health_returns_200_db_ok() -> None:
    mock_conn = AsyncMock()
    with patch(
        "carpix_images.routers.health.asyncpg.connect", return_value=mock_conn
    ):
        client = TestClient(create_app())
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


def test_health_returns_200_db_unreachable() -> None:
    with patch(
        "carpix_images.routers.health.asyncpg.connect",
        side_effect=Exception("connection refused"),
    ):
        client = TestClient(create_app())
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "error"}


def test_docs_accessible() -> None:
    client = TestClient(create_app())
    response = client.get("/docs")
    assert response.status_code == 200
