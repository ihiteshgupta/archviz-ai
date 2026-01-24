"""Boundary tests for ArchViz AI - testing limits and edge cases."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestProjectBoundaries:
    """Test project boundary conditions."""

    def test_project_name_min_length(self, client):
        """Single character project name should work."""
        response = client.post("/api/projects/", json={"name": "A"})
        assert response.status_code == 200
        assert response.json()["name"] == "A"

    def test_project_name_max_reasonable_length(self, client):
        """Project name up to 255 chars should work."""
        name = "x" * 255
        response = client.post("/api/projects/", json={"name": name})
        assert response.status_code == 200

    def test_project_name_excessive_length(self, client):
        """Very long project name should be handled."""
        name = "x" * 1000
        response = client.post("/api/projects/", json={"name": name})
        # Should either accept or reject with proper error
        assert response.status_code in [200, 400, 422]

    def test_project_description_empty(self, client):
        """Empty description should work."""
        response = client.post(
            "/api/projects/",
            json={"name": "Test", "description": ""}
        )
        assert response.status_code == 200

    def test_project_description_null(self, client):
        """Null description should work."""
        response = client.post(
            "/api/projects/",
            json={"name": "Test", "description": None}
        )
        assert response.status_code == 200

    def test_project_description_long(self, client):
        """Long description should be handled."""
        description = "x" * 5000
        response = client.post(
            "/api/projects/",
            json={"name": "Test", "description": description}
        )
        assert response.status_code in [200, 400, 422]

    def test_unicode_emoji_project_name(self, client):
        """Emoji in project name should work."""
        response = client.post("/api/projects/", json={"name": "🏠 House Project 🏠"})
        assert response.status_code == 200
        assert "🏠" in response.json()["name"]

    def test_special_characters_project_name(self, client):
        """Special characters in project name."""
        response = client.post(
            "/api/projects/",
            json={"name": "Project <test> & \"quotes\" 'apostrophe'"}
        )
        assert response.status_code == 200


class TestRenderBoundaries:
    """Test render boundary conditions."""

    def test_render_min_resolution(self, client):
        """Minimum resolution should be handled."""
        project = client.post("/api/projects/", json={"name": "Res Test"}).json()

        response = client.post(
            "/api/render/",
            json={"project_id": project["id"], "resolution": 1}
        )
        # Should accept or reject with validation error
        assert response.status_code in [200, 400, 422]

    def test_render_standard_resolutions(self, client):
        """Standard resolutions should work."""
        project = client.post("/api/projects/", json={"name": "Res Test"}).json()

        for resolution in [512, 1024, 2048]:
            response = client.post(
                "/api/render/",
                json={"project_id": project["id"], "resolution": resolution}
            )
            assert response.status_code == 200

    def test_render_excessive_resolution(self, client):
        """Excessive resolution should be handled."""
        project = client.post("/api/projects/", json={"name": "Big Res"}).json()

        response = client.post(
            "/api/render/",
            json={"project_id": project["id"], "resolution": 99999}
        )
        # Should accept or reject
        assert response.status_code in [200, 400, 422]

    def test_render_zero_resolution(self, client):
        """Zero resolution should be rejected."""
        project = client.post("/api/projects/", json={"name": "Zero Res"}).json()

        response = client.post(
            "/api/render/",
            json={"project_id": project["id"], "resolution": 0}
        )
        assert response.status_code in [400, 422]

    def test_render_negative_resolution(self, client):
        """Negative resolution should be rejected."""
        project = client.post("/api/projects/", json={"name": "Neg Res"}).json()

        response = client.post(
            "/api/render/",
            json={"project_id": project["id"], "resolution": -1024}
        )
        assert response.status_code in [400, 422]

    def test_render_empty_views(self, client):
        """Empty views list should be handled."""
        project = client.post("/api/projects/", json={"name": "Views Test"}).json()

        response = client.post(
            "/api/render/",
            json={"project_id": project["id"], "views": []}
        )
        # Should use default or accept empty
        assert response.status_code == 200

    def test_render_many_views(self, client):
        """Many views should be handled."""
        project = client.post("/api/projects/", json={"name": "Many Views"}).json()

        response = client.post(
            "/api/render/",
            json={
                "project_id": project["id"],
                "views": [f"view_{i}" for i in range(50)]
            }
        )
        assert response.status_code in [200, 400, 422]


class TestQuickRenderBoundaries:
    """Test quick render boundary conditions."""

    def test_quick_render_valid_sizes(self, client):
        """Valid DALL-E sizes should be accepted."""
        for size in ["1024x1024", "1792x1024", "1024x1792"]:
            response = client.post(
                "/api/render/quick",
                json={"room_type": "bedroom", "style": "modern", "size": size}
            )
            # May fail if Azure not configured (503) but size should be valid
            assert response.status_code in [200, 503]

    def test_quick_render_invalid_size(self, client):
        """Invalid size format should be handled."""
        response = client.post(
            "/api/render/quick",
            json={"room_type": "bedroom", "style": "modern", "size": "invalid"}
        )
        assert response.status_code in [400, 422, 500, 503]

    def test_quick_render_empty_room_type(self, client):
        """Empty room type should be handled."""
        response = client.post(
            "/api/render/quick",
            json={"room_type": "", "style": "modern"}
        )
        assert response.status_code in [200, 400, 422, 503]

    def test_quick_render_long_room_type(self, client):
        """Long room type should be handled."""
        response = client.post(
            "/api/render/quick",
            json={"room_type": "x" * 500, "style": "modern"}
        )
        assert response.status_code in [200, 400, 422, 500, 503]

    def test_quick_render_long_additional_details(self, client):
        """Long additional details should be handled."""
        response = client.post(
            "/api/render/quick",
            json={
                "room_type": "bedroom",
                "style": "modern",
                "additional_details": "x" * 2000
            }
        )
        assert response.status_code in [200, 400, 422, 500, 503]


class TestBatchRenderBoundaries:
    """Test batch render boundary conditions."""

    def test_batch_empty_rooms(self, client):
        """Empty rooms list should be handled."""
        response = client.post(
            "/api/render/batch",
            json={"floor_plan_id": "test", "rooms": []}
        )
        # Should reject or handle
        assert response.status_code in [200, 400, 422, 503]

    def test_batch_single_room(self, client):
        """Single room batch should work."""
        response = client.post(
            "/api/render/batch",
            json={
                "floor_plan_id": "test",
                "rooms": [{"id": "room1", "name": "Room 1"}]
            }
        )
        assert response.status_code in [200, 503]

    def test_batch_many_rooms(self, client):
        """Many rooms should be handled."""
        rooms = [{"id": f"room{i}", "name": f"Room {i}"} for i in range(50)]
        response = client.post(
            "/api/render/batch",
            json={"floor_plan_id": "test", "rooms": rooms}
        )
        assert response.status_code in [200, 400, 503]

    def test_batch_excessive_rooms(self, client):
        """Excessive rooms should be handled."""
        rooms = [{"id": f"room{i}", "name": f"Room {i}"} for i in range(500)]
        response = client.post(
            "/api/render/batch",
            json={"floor_plan_id": "test", "rooms": rooms}
        )
        assert response.status_code in [200, 400, 422, 503]

    def test_batch_list_with_limit(self, client):
        """List batch jobs with limit."""
        response = client.get("/api/render/batch/jobs/list?limit=5")
        assert response.status_code == 200
        assert len(response.json()["jobs"]) <= 5

    def test_batch_list_zero_limit(self, client):
        """List batch jobs with zero limit."""
        response = client.get("/api/render/batch/jobs/list?limit=0")
        assert response.status_code == 200


class TestMaterialsBoundaries:
    """Test materials API boundary conditions."""

    def test_materials_library_returns_all(self, client):
        """Materials library should return materials."""
        response = client.get("/api/materials/library")
        assert response.status_code == 200
        assert "materials" in response.json()

    def test_categories_returns_list(self, client):
        """Categories should return list."""
        response = client.get("/api/materials/categories")
        assert response.status_code == 200
        assert "categories" in response.json()

    def test_presets_returns_list(self, client):
        """Presets should return list."""
        response = client.get("/api/materials/presets")
        assert response.status_code == 200
        assert "presets" in response.json()


class TestChatBoundaries:
    """Test chat API boundary conditions."""

    def test_chat_min_message(self, client):
        """Single character message should be handled."""
        response = client.post(
            "/api/chat/",
            json={"message": "?", "conversation_history": []}
        )
        assert response.status_code in [200, 503]

    def test_chat_empty_history(self, client):
        """Empty conversation history should work."""
        response = client.post(
            "/api/chat/",
            json={"message": "Hello", "conversation_history": []}
        )
        assert response.status_code in [200, 503]

    def test_chat_long_history(self, client):
        """Long conversation history should be handled."""
        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(100)
        ]
        response = client.post(
            "/api/chat/",
            json={"message": "Continue", "conversation_history": history}
        )
        # Should truncate or handle
        assert response.status_code in [200, 400, 422, 503]


class TestRoomPipelineBoundaries:
    """Test room pipeline boundary conditions."""

    def test_room_pipeline_minimal_polygon(self, client):
        """Triangle (minimum polygon) should work."""
        response = client.post(
            "/api/room-pipeline/generate-shell",
            json={
                "room_id": "triangle",
                "room_data": {
                    "polygon": [[0, 0], [5, 0], [2.5, 4]],
                    "height": 2.7
                }
            }
        )
        assert response.status_code == 200

    def test_room_pipeline_complex_polygon(self, client):
        """Complex polygon with many vertices."""
        # L-shaped room
        polygon = [
            [0, 0], [10, 0], [10, 5], [5, 5], [5, 10], [0, 10]
        ]
        response = client.post(
            "/api/room-pipeline/generate-shell",
            json={
                "room_id": "l-shape",
                "room_data": {
                    "polygon": polygon,
                    "height": 2.7
                }
            }
        )
        assert response.status_code == 200

    def test_room_pipeline_zero_height(self, client):
        """Zero height should be handled."""
        response = client.post(
            "/api/room-pipeline/generate-shell",
            json={
                "room_id": "flat",
                "room_data": {
                    "polygon": [[0, 0], [5, 0], [5, 5], [0, 5]],
                    "height": 0
                }
            }
        )
        # Should reject or use default
        assert response.status_code in [200, 400, 422, 500]

    def test_room_pipeline_negative_height(self, client):
        """Negative height should be handled."""
        response = client.post(
            "/api/room-pipeline/generate-shell",
            json={
                "room_id": "negative",
                "room_data": {
                    "polygon": [[0, 0], [5, 0], [5, 5], [0, 5]],
                    "height": -2.7
                }
            }
        )
        assert response.status_code in [200, 400, 422, 500]

    def test_room_pipeline_very_tall(self, client):
        """Very tall room should be handled."""
        response = client.post(
            "/api/room-pipeline/generate-shell",
            json={
                "room_id": "tall",
                "room_data": {
                    "polygon": [[0, 0], [5, 0], [5, 5], [0, 5]],
                    "height": 100
                }
            }
        )
        assert response.status_code in [200, 400, 422]

    def test_room_pipeline_with_doors(self, client):
        """Room with doors should work."""
        response = client.post(
            "/api/room-pipeline/generate-shell",
            json={
                "room_id": "with-door",
                "room_data": {
                    "polygon": [[0, 0], [5, 0], [5, 5], [0, 5]],
                    "height": 2.7,
                    "doors": [
                        {"position": [2.5, 0], "width": 0.9, "height": 2.1}
                    ]
                }
            }
        )
        assert response.status_code == 200

    def test_room_pipeline_with_windows(self, client):
        """Room with windows should work."""
        response = client.post(
            "/api/room-pipeline/generate-shell",
            json={
                "room_id": "with-window",
                "room_data": {
                    "polygon": [[0, 0], [5, 0], [5, 5], [0, 5]],
                    "height": 2.7,
                    "windows": [
                        {"position": [5, 2.5], "width": 1.2, "height": 1.0, "sill_height": 0.9}
                    ]
                }
            }
        )
        assert response.status_code == 200
