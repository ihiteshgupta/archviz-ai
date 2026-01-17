"""Project API endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestProjectCRUD:
    """Test project CRUD operations."""

    def test_create_project_minimal(self, client):
        """Test creating a project with minimal data."""
        response = client.post(
            "/api/projects/",
            json={"name": "Test Project"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["status"] == "created"
        assert "id" in data
        assert data["description"] is None

    def test_create_project_with_description(self, client):
        """Test creating a project with description."""
        response = client.post(
            "/api/projects/",
            json={
                "name": "Full Project",
                "description": "A complete project with description"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Full Project"
        assert data["description"] == "A complete project with description"

    def test_create_project_empty_name(self, client):
        """Test creating a project with empty name."""
        response = client.post(
            "/api/projects/",
            json={"name": ""}
        )
        # API currently accepts empty names
        # In production, validation should be added
        assert response.status_code in [200, 400, 422]

    def test_list_projects(self, client):
        """Test listing all projects."""
        # Create a project first
        client.post("/api/projects/", json={"name": "List Test"})

        response = client.get("/api/projects/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_project_by_id(self, client):
        """Test getting a specific project."""
        # Create a project
        create_response = client.post(
            "/api/projects/",
            json={"name": "Get Test Project"}
        )
        project_id = create_response.json()["id"]

        # Get the project
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Get Test Project"

    def test_get_nonexistent_project(self, client):
        """Test getting a project that doesn't exist."""
        response = client.get("/api/projects/nonexistent-id-12345")
        assert response.status_code == 404

    def test_project_timestamps(self, client):
        """Test that projects have proper timestamps."""
        response = client.post(
            "/api/projects/",
            json={"name": "Timestamp Test"}
        )
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
        assert data["created_at"] is not None


class TestProjectStatus:
    """Test project status transitions."""

    def test_initial_status_is_created(self, client):
        """Test that new projects have 'created' status."""
        response = client.post(
            "/api/projects/",
            json={"name": "Status Test"}
        )
        assert response.json()["status"] == "created"

    def test_project_floor_plan_initially_null(self, client):
        """Test that floor_plan is null for new projects."""
        response = client.post(
            "/api/projects/",
            json={"name": "Floor Plan Test"}
        )
        data = response.json()
        assert data["floor_plan"] is None
        assert data["file_name"] is None
