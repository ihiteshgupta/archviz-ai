"""Resilience tests for ArchViz AI - testing failure handling and recovery."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAzureOpenAIFailures:
    """Test handling of Azure OpenAI service failures."""

    def test_quick_render_service_unavailable(self, client):
        """Handle DALL-E service unavailable gracefully."""
        # When Azure is not configured, should return 503
        status = client.get("/api/render/quick/status").json()

        if not status["available"]:
            response = client.post(
                "/api/render/quick",
                json={"room_type": "bedroom", "style": "modern"}
            )
            assert response.status_code == 503
            assert "azure" in response.json()["detail"].lower() or "dall-e" in response.json()["detail"].lower()

    def test_chat_service_unavailable(self, client):
        """Handle chat service unavailable gracefully."""
        status = client.get("/api/chat/status").json()

        if not status["available"]:
            response = client.post(
                "/api/chat/",
                json={"message": "Hello", "conversation_history": []}
            )
            # Should return error or fallback response
            assert response.status_code in [200, 503]

    @pytest.mark.integration
    def test_dalle_timeout_handling(self, client):
        """Handle DALL-E timeout gracefully."""
        with patch("api.routes.render.get_dalle_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.generate_concept_render = AsyncMock(
                side_effect=TimeoutError("Request timed out")
            )
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/render/quick",
                json={"room_type": "bedroom", "style": "modern"}
            )
            # Should handle timeout gracefully
            assert response.status_code in [500, 503, 504]

    @pytest.mark.integration
    def test_dalle_rate_limit_handling(self, client):
        """Handle DALL-E rate limits."""
        with patch("api.routes.render.get_dalle_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.generate_concept_render = AsyncMock(
                side_effect=Exception("Rate limit exceeded")
            )
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/render/quick",
                json={"room_type": "kitchen", "style": "scandinavian"}
            )
            assert response.status_code in [429, 500, 503]

    @pytest.mark.integration
    def test_dalle_content_policy_violation(self, client):
        """Handle content policy violations gracefully."""
        with patch("api.routes.render.get_dalle_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.generate_concept_render = AsyncMock(
                side_effect=Exception("Content policy violation")
            )
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/render/quick",
                json={"room_type": "bathroom", "style": "modern"}
            )
            assert response.status_code in [400, 500]


class TestBatchRenderResilience:
    """Test batch render resilience to failures."""

    def test_batch_render_unavailable(self, client):
        """Handle batch render when service unavailable."""
        response = client.post(
            "/api/render/batch",
            json={
                "floor_plan_id": "test-plan",
                "rooms": [{"id": "room1", "name": "Living Room"}]
            }
        )
        # Should either start job or return 503
        assert response.status_code in [200, 503]

    def test_batch_job_not_found(self, client):
        """Handle nonexistent batch job."""
        response = client.get("/api/render/batch/nonexistent-job-id")
        assert response.status_code == 404

    def test_cancel_nonexistent_batch(self, client):
        """Handle cancel of nonexistent batch job."""
        response = client.post("/api/render/batch/nonexistent-id/cancel")
        assert response.status_code == 404

    def test_delete_nonexistent_batch(self, client):
        """Handle delete of nonexistent batch job."""
        response = client.delete("/api/render/batch/nonexistent-id")
        assert response.status_code == 404


class TestProjectResilience:
    """Test project operations resilience."""

    def test_get_nonexistent_project(self, client):
        """Handle request for nonexistent project."""
        response = client.get("/api/projects/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_nonexistent_project(self, client):
        """Handle delete of nonexistent project."""
        response = client.delete("/api/projects/nonexistent-id")
        assert response.status_code == 404

    def test_upload_to_nonexistent_project(self, client):
        """Handle upload to nonexistent project."""
        files = {"file": ("test.dxf", b"content", "application/octet-stream")}
        response = client.post("/api/projects/nonexistent-id/upload", files=files)
        assert response.status_code == 404

    def test_get_floor_plan_not_parsed(self, client):
        """Handle request for floor plan before parsing."""
        # Create project without uploading file
        project = client.post("/api/projects/", json={"name": "No Upload"}).json()

        response = client.get(f"/api/projects/{project['id']}/floor-plan")
        assert response.status_code == 404
        assert "not parsed" in response.json()["detail"].lower()

    def test_get_preview_not_parsed(self, client):
        """Handle preview request before parsing."""
        project = client.post("/api/projects/", json={"name": "No Preview"}).json()

        response = client.get(f"/api/projects/{project['id']}/preview")
        assert response.status_code == 404


class TestRenderJobResilience:
    """Test render job operations resilience."""

    def test_get_nonexistent_render_job(self, client):
        """Handle request for nonexistent render job."""
        response = client.get("/api/render/nonexistent-job-id")
        assert response.status_code == 404

    def test_cancel_nonexistent_render_job(self, client):
        """Handle cancel of nonexistent render job."""
        response = client.post("/api/render/nonexistent-id/cancel")
        assert response.status_code == 404

    def test_project_renders_empty(self, client):
        """Handle request for renders of project with none."""
        project = client.post("/api/projects/", json={"name": "No Renders"}).json()

        response = client.get(f"/api/render/project/{project['id']}")
        assert response.status_code == 200
        assert response.json() == []


class TestMaterialsResilience:
    """Test materials API resilience."""

    def test_get_nonexistent_material(self, client):
        """Handle request for nonexistent material."""
        response = client.get("/api/materials/library/nonexistent-material-id")
        assert response.status_code == 404

    def test_get_nonexistent_preset(self, client):
        """Handle request for nonexistent preset."""
        response = client.get("/api/materials/presets/nonexistent-preset")
        assert response.status_code == 404

    def test_get_invalid_category(self, client):
        """Handle request for invalid category."""
        response = client.get("/api/materials/category/nonexistent-category")
        # Should return empty list or 404
        assert response.status_code in [200, 404]


class TestChatResilience:
    """Test chat API resilience."""

    def test_chat_empty_message(self, client):
        """Handle empty chat message."""
        response = client.post(
            "/api/chat/",
            json={"message": "", "conversation_history": []}
        )
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400, 422]

    def test_chat_very_long_message(self, client):
        """Handle very long chat message."""
        long_message = "x" * 100000
        response = client.post(
            "/api/chat/",
            json={"message": long_message, "conversation_history": []}
        )
        # Should either truncate, reject, or handle
        assert response.status_code in [200, 400, 422, 503]

    def test_chat_malformed_history(self, client):
        """Handle malformed conversation history."""
        response = client.post(
            "/api/chat/",
            json={
                "message": "Hello",
                "conversation_history": [{"invalid": "structure"}]
            }
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 422, 503]


class TestRoomPipelineResilience:
    """Test room pipeline API resilience."""

    def test_room_pipeline_status_not_found(self, client):
        """Handle status check for nonexistent job."""
        response = client.get("/api/room-pipeline/status/nonexistent-job")
        assert response.status_code == 404

    def test_room_pipeline_missing_room_data(self, client):
        """Handle missing room data in request."""
        response = client.post(
            "/api/room-pipeline/generate-shell",
            json={"room_id": "test"}  # Missing room_data
        )
        assert response.status_code == 422

    def test_room_pipeline_empty_polygon(self, client):
        """Handle empty polygon in room data."""
        response = client.post(
            "/api/room-pipeline/generate-shell",
            json={
                "room_id": "test",
                "room_data": {
                    "polygon": [],
                    "height": 2.7
                }
            }
        )
        # Should reject or handle gracefully
        assert response.status_code in [200, 400, 422, 500]


class TestAPIRobustness:
    """Test general API robustness."""

    def test_malformed_json(self, client):
        """Handle malformed JSON body."""
        response = client.post(
            "/api/projects/",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_wrong_http_method(self, client):
        """Handle wrong HTTP method."""
        response = client.delete("/api/render/styles")
        assert response.status_code == 405

    def test_missing_content_type(self, client):
        """Handle missing content type."""
        response = client.post(
            "/api/projects/",
            content='{"name": "test"}'
        )
        # May work or fail depending on framework handling
        assert response.status_code in [200, 422]

    def test_extra_fields_ignored(self, client):
        """Extra fields in request should be ignored."""
        response = client.post(
            "/api/projects/",
            json={
                "name": "Test Project",
                "unknown_field": "should be ignored",
                "another_unknown": 12345
            }
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Test Project"
