"""API tests for project endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db


@pytest.fixture
async def client(db_session):
    """Async HTTP client with overridden DB dependency."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestProjectAPI:
    """Project CRUD endpoint tests."""

    async def test_create_project_success(self, client):
        response = await client.post("/api/projects/", json={
            "title": "Test Novel",
            "genre": "Fantasy",
            "target_words": 100000,
        })
        assert response.status_code == 200
        data = response.json()
        # Projects router doesn't use ApiResponse yet, so check structure
        assert "id" in data or "code" in data

    async def test_list_projects_empty(self, client):
        response = await client.get("/api/projects/")
        assert response.status_code == 200

    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestErrorHandling:
    """Error handling tests."""

    async def test_health_check_db_down(self, mocker):
        mocker.patch(
            "app.database.DatabaseEngine.get_engine",
            side_effect=ConnectionError("DB unavailable"),
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            # Health endpoint doesn't require DB, should still return 200
            assert response.status_code == 200
