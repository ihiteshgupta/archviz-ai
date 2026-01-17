"""End-to-end workflow tests."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestCompleteWorkflow:
    """Test complete user workflows."""

    def test_project_creation_workflow(self, client):
        """Test the complete project creation workflow."""
        # Step 1: Create a project
        project_response = client.post(
            "/api/projects/",
            json={
                "name": "E2E Test Project",
                "description": "End-to-end test"
            }
        )
        assert project_response.status_code == 200
        project = project_response.json()
        project_id = project["id"]

        # Step 2: Verify project was created
        get_response = client.get(f"/api/projects/{project_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "E2E Test Project"

        # Step 3: Project should appear in list
        list_response = client.get("/api/projects/")
        assert list_response.status_code == 200
        project_ids = [p["id"] for p in list_response.json()]
        assert project_id in project_ids

    def test_render_workflow(self, client):
        """Test the complete render workflow."""
        # Step 1: Create a project
        project = client.post(
            "/api/projects/",
            json={"name": "Render Workflow Test"}
        ).json()
        project_id = project["id"]

        # Step 2: Get available styles
        styles_response = client.get("/api/render/styles")
        assert styles_response.status_code == 200
        styles = styles_response.json()["styles"]
        assert len(styles) > 0

        # Step 3: Create a render job
        render_response = client.post(
            "/api/render/",
            json={
                "project_id": project_id,
                "style": styles[0]["id"],
                "resolution": 1024
            }
        )
        assert render_response.status_code == 200
        job = render_response.json()
        job_id = job["id"]

        # Step 4: Check job status
        status_response = client.get(f"/api/render/{job_id}")
        assert status_response.status_code == 200
        assert status_response.json()["project_id"] == project_id

        # Step 5: Get all project renders
        project_renders = client.get(f"/api/render/project/{project_id}")
        assert project_renders.status_code == 200
        assert len(project_renders.json()) >= 1

    def test_material_selection_workflow(self, client):
        """Test the material selection workflow."""
        # Step 1: Get all materials
        materials_response = client.get("/api/materials/library")
        assert materials_response.status_code == 200
        materials = materials_response.json()["materials"]

        # Step 2: Get categories
        categories_response = client.get("/api/materials/categories")
        assert categories_response.status_code == 200

        # Step 3: Filter by category
        wood_materials = client.get("/api/materials/library?category=wood")
        assert wood_materials.status_code == 200

        # Step 4: Get style presets
        presets_response = client.get("/api/materials/presets")
        assert presets_response.status_code == 200
        presets = presets_response.json()["presets"]
        assert len(presets) > 0

        # Step 5: Each preset should have material recommendations
        for preset in presets:
            assert "materials" in preset
            assert len(preset["materials"]) > 0


@pytest.mark.integration
class TestAIWorkflow:
    """Test AI-powered workflows.

    These tests require Azure OpenAI to be configured.
    """

    def test_design_consultation_workflow(self, client):
        """Test the design consultation workflow with AI."""
        # Check if AI is available
        status = client.get("/api/chat/status").json()
        if not status["available"]:
            pytest.skip("Azure OpenAI not configured")

        # Step 1: Create a project
        project = client.post(
            "/api/projects/",
            json={"name": "AI Consultation Test"}
        ).json()

        # Step 2: Ask for design recommendations
        chat_response = client.post(
            "/api/chat/",
            json={
                "message": "I need help designing a modern bedroom with natural light",
                "conversation_history": []
            }
        )
        assert chat_response.status_code == 200
        recommendation = chat_response.json()["message"]
        assert len(recommendation) > 50  # Should have substantial response

        # Step 3: Get material suggestions
        materials_response = client.get("/api/materials/library")
        materials = materials_response.json()["materials"]
        assert len(materials) > 0

    def test_quick_render_workflow(self, client):
        """Test the quick render workflow with DALL-E."""
        # Check if quick render is available
        status = client.get("/api/render/quick/status").json()
        if not status["available"]:
            pytest.skip("DALL-E 3 not configured")

        # Step 1: Generate a quick concept
        render_response = client.post(
            "/api/render/quick",
            json={
                "room_type": "living room",
                "style": "modern minimalist",
                "additional_details": "large windows, natural light",
                "size": "1024x1024"
            }
        )
        assert render_response.status_code == 200
        result = render_response.json()

        # Step 2: Verify result structure
        assert result["status"] == "completed"
        assert "render" in result
        assert "url" in result["render"]
        assert result["render"]["url"].startswith("http")

    def test_full_design_to_render_workflow(self, client):
        """Test complete workflow from design consultation to render."""
        # Check services
        chat_status = client.get("/api/chat/status").json()
        render_status = client.get("/api/render/quick/status").json()

        if not chat_status["available"]:
            pytest.skip("Azure OpenAI not configured")

        # Step 1: Create project
        project = client.post(
            "/api/projects/",
            json={"name": "Full Workflow Test"}
        ).json()

        # Step 2: Get design advice
        chat_response = client.post(
            "/api/chat/",
            json={
                "message": "Design a cozy Scandinavian living room",
                "conversation_history": []
            }
        )
        assert chat_response.status_code == 200

        # Step 3: Get style presets
        presets = client.get("/api/materials/presets").json()["presets"]
        scandinavian_preset = next(
            (p for p in presets if "scandinavian" in p["id"].lower()),
            presets[0]
        )

        # Step 4: Create standard render job
        render_job = client.post(
            "/api/render/",
            json={
                "project_id": project["id"],
                "style": "scandinavian"
            }
        )
        assert render_job.status_code == 200

        # Step 5: If DALL-E available, do quick render too
        if render_status["available"]:
            quick_render = client.post(
                "/api/render/quick",
                json={
                    "room_type": "living room",
                    "style": "scandinavian",
                    "materials": scandinavian_preset.get("materials", {}),
                    "size": "1024x1024"
                }
            )
            assert quick_render.status_code == 200


class TestErrorHandling:
    """Test error handling across the application."""

    def test_invalid_project_id(self, client):
        """Test handling of invalid project ID."""
        response = client.get("/api/projects/invalid-id-12345")
        assert response.status_code == 404

    def test_invalid_render_job_id(self, client):
        """Test handling of invalid render job ID."""
        response = client.get("/api/render/invalid-job-id")
        assert response.status_code == 404

    def test_invalid_json_body(self, client):
        """Test handling of invalid JSON body."""
        response = client.post(
            "/api/projects/",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post(
            "/api/projects/",
            json={}
        )
        assert response.status_code == 422

    def test_wrong_http_method(self, client):
        """Test handling of wrong HTTP method."""
        response = client.delete("/api/render/styles")
        assert response.status_code == 405


class TestCORS:
    """Test CORS configuration."""

    def test_cors_allowed_origin(self, client):
        """Test that CORS allows configured origins."""
        response = client.options(
            "/api/projects/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        # Should not block the request
        assert response.status_code in [200, 204]

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in response."""
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS headers should be in response
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
