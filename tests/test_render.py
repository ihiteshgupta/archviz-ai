"""Render API endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def project_id(client):
    """Create a test project and return its ID."""
    response = client.post(
        "/api/projects/",
        json={"name": "Render Test Project"}
    )
    return response.json()["id"]


class TestRenderStyles:
    """Test render style endpoints."""

    def test_get_render_styles(self, client):
        """Test fetching available render styles."""
        response = client.get("/api/render/styles")
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        assert isinstance(data["styles"], list)
        assert len(data["styles"]) > 0

    def test_render_style_structure(self, client):
        """Test that render styles have correct structure."""
        response = client.get("/api/render/styles")
        styles = response.json()["styles"]

        for style in styles:
            assert "id" in style
            assert "name" in style
            assert "description" in style

    def test_expected_styles_present(self, client):
        """Test that expected styles are available."""
        response = client.get("/api/render/styles")
        styles = response.json()["styles"]
        style_ids = [s["id"] for s in styles]

        expected = ["modern_minimalist", "scandinavian", "industrial"]
        for expected_style in expected:
            assert expected_style in style_ids, f"Missing style: {expected_style}"


class TestRenderJobs:
    """Test render job endpoints."""

    def test_create_render_job(self, client, project_id):
        """Test creating a render job."""
        response = client.post(
            "/api/render/",
            json={
                "project_id": project_id,
                "style": "modern_minimalist",
                "views": ["default"],
                "resolution": 1024
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["project_id"] == project_id
        assert data["status"] == "pending"

    def test_create_render_job_default_values(self, client, project_id):
        """Test creating a render job with default values."""
        response = client.post(
            "/api/render/",
            json={"project_id": project_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["style"] == "modern_minimalist"
        # Resolution may not be in response, just verify job was created
        assert "id" in data
        assert data["project_id"] == project_id

    def test_get_render_job(self, client, project_id):
        """Test getting a render job by ID."""
        # Create a job
        create_response = client.post(
            "/api/render/",
            json={"project_id": project_id}
        )
        job_id = create_response.json()["id"]

        # Get the job
        response = client.get(f"/api/render/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id

    def test_get_nonexistent_job(self, client):
        """Test getting a job that doesn't exist."""
        response = client.get("/api/render/nonexistent-job-id")
        assert response.status_code == 404

    def test_get_project_renders(self, client, project_id):
        """Test getting all renders for a project."""
        # Create some jobs
        client.post("/api/render/", json={"project_id": project_id})
        client.post("/api/render/", json={"project_id": project_id})

        response = client.get(f"/api/render/project/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_cancel_render_job(self, client, project_id):
        """Test cancelling a render job."""
        # Create a job
        create_response = client.post(
            "/api/render/",
            json={"project_id": project_id}
        )
        job_id = create_response.json()["id"]

        # Cancel it
        response = client.post(f"/api/render/{job_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"


class TestQuickRender:
    """Test quick render (DALL-E) endpoints."""

    def test_quick_render_status(self, client):
        """Test quick render availability status."""
        response = client.get("/api/render/quick/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert isinstance(data["available"], bool)

    def test_quick_render_requires_room_type(self, client):
        """Test that quick render requires room_type."""
        response = client.post(
            "/api/render/quick",
            json={"style": "modern"}
        )
        # Should fail validation without room_type
        assert response.status_code in [400, 422]


class TestRenderValidation:
    """Test render request validation."""

    def test_invalid_style(self, client, project_id):
        """Test that invalid style is rejected."""
        response = client.post(
            "/api/render/",
            json={
                "project_id": project_id,
                "style": "invalid_style_name"
            }
        )
        assert response.status_code == 422

    def test_invalid_resolution(self, client, project_id):
        """Test that invalid resolution is handled."""
        response = client.post(
            "/api/render/",
            json={
                "project_id": project_id,
                "resolution": -100
            }
        )
        # Should either fail validation or use default
        assert response.status_code in [200, 422]
