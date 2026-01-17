"""Basic API tests."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ArchViz AI"
    assert data["status"] == "running"


def test_get_render_styles(client):
    """Test render styles endpoint."""
    response = client.get("/api/render/styles")
    assert response.status_code == 200
    data = response.json()
    assert "styles" in data
    assert len(data["styles"]) > 0


def test_get_material_library(client):
    """Test material library endpoint."""
    response = client.get("/api/materials/library")
    assert response.status_code == 200
    data = response.json()
    assert "materials" in data
    assert len(data["materials"]) > 0


def test_get_categories(client):
    """Test categories endpoint."""
    response = client.get("/api/materials/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data


def test_get_style_presets(client):
    """Test style presets endpoint."""
    response = client.get("/api/materials/presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert len(data["presets"]) > 0


def test_create_project(client):
    """Test project creation."""
    response = client.post(
        "/api/projects/",
        json={"name": "Test Project", "description": "A test project"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["status"] == "created"
    assert "id" in data


def test_list_projects(client):
    """Test project listing."""
    response = client.get("/api/projects/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_chat_status(client):
    """Test chat status endpoint."""
    response = client.get("/api/chat/status")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data


def test_quick_render_status(client):
    """Test quick render status endpoint."""
    response = client.get("/api/render/quick/status")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
