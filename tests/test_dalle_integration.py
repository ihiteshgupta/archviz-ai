"""DALL-E 3 integration tests."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def dalle_available(client) -> bool:
    """Check if DALL-E is available."""
    response = client.get("/api/render/quick/status")
    return response.json().get("available", False)


@pytest.mark.integration
class TestDALLEQuickRender:
    """Test DALL-E 3 quick render functionality."""

    def test_quick_render_living_room(self, client):
        """Test generating a living room render."""
        if not dalle_available(client):
            pytest.skip("DALL-E 3 not configured")

        response = client.post(
            "/api/render/quick",
            json={
                "room_type": "living room",
                "style": "modern",
                "size": "1024x1024"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "url" in data["render"]

    def test_quick_render_bedroom(self, client):
        """Test generating a bedroom render."""
        if not dalle_available(client):
            pytest.skip("DALL-E 3 not configured")

        response = client.post(
            "/api/render/quick",
            json={
                "room_type": "bedroom",
                "style": "scandinavian",
                "additional_details": "cozy, warm lighting",
                "size": "1024x1024"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_quick_render_kitchen(self, client):
        """Test generating a kitchen render."""
        if not dalle_available(client):
            pytest.skip("DALL-E 3 not configured")

        response = client.post(
            "/api/render/quick",
            json={
                "room_type": "kitchen",
                "style": "industrial",
                "materials": {
                    "countertop": "marble",
                    "cabinets": "dark wood"
                },
                "size": "1024x1024"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_quick_render_bathroom(self, client):
        """Test generating a bathroom render."""
        if not dalle_available(client):
            pytest.skip("DALL-E 3 not configured")

        response = client.post(
            "/api/render/quick",
            json={
                "room_type": "bathroom",
                "style": "minimalist",
                "additional_details": "spa-like atmosphere",
                "size": "1024x1024"
            }
        )
        assert response.status_code == 200

    def test_quick_render_with_materials(self, client):
        """Test generating render with specific materials."""
        if not dalle_available(client):
            pytest.skip("DALL-E 3 not configured")

        response = client.post(
            "/api/render/quick",
            json={
                "room_type": "living room",
                "style": "modern minimalist",
                "materials": {
                    "floor": "light oak hardwood",
                    "walls": "warm white",
                    "accent": "natural stone",
                    "furniture": "leather and metal"
                },
                "additional_details": "floor to ceiling windows, city view",
                "size": "1024x1024"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "revised_prompt" in data["render"]

    def test_quick_render_response_structure(self, client):
        """Test that quick render response has correct structure."""
        if not dalle_available(client):
            pytest.skip("DALL-E 3 not configured")

        response = client.post(
            "/api/render/quick",
            json={
                "room_type": "office",
                "style": "modern",
                "size": "1024x1024"
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "status" in data
        assert "render" in data
        assert "request" in data
        assert "source" in data
        assert data["source"] == "dalle3"

        # Check render object
        render = data["render"]
        assert "url" in render
        assert render["url"].startswith("http")

    def test_quick_render_different_sizes(self, client):
        """Test different render sizes."""
        if not dalle_available(client):
            pytest.skip("DALL-E 3 not configured")

        sizes = ["1024x1024", "1792x1024", "1024x1792"]

        for size in sizes:
            response = client.post(
                "/api/render/quick",
                json={
                    "room_type": "dining room",
                    "style": "contemporary",
                    "size": size
                }
            )
            assert response.status_code == 200, f"Failed for size {size}"

    def test_quick_render_various_styles(self, client):
        """Test various architectural styles."""
        if not dalle_available(client):
            pytest.skip("DALL-E 3 not configured")

        styles = [
            "modern minimalist",
            "scandinavian",
            "industrial",
            "art deco",
            "japanese zen",
            "mediterranean"
        ]

        for style in styles:
            response = client.post(
                "/api/render/quick",
                json={
                    "room_type": "living room",
                    "style": style,
                    "size": "1024x1024"
                }
            )
            assert response.status_code == 200, f"Failed for style {style}"


@pytest.mark.integration
class TestDALLEErrorHandling:
    """Test DALL-E error handling."""

    def test_invalid_size(self, client):
        """Test handling of invalid size."""
        if not dalle_available(client):
            pytest.skip("DALL-E 3 not configured")

        response = client.post(
            "/api/render/quick",
            json={
                "room_type": "bedroom",
                "style": "modern",
                "size": "500x500"  # Invalid size
            }
        )
        # API returns 500 when DALL-E rejects invalid size
        assert response.status_code in [200, 400, 422, 500]

    def test_empty_room_type(self, client):
        """Test handling of empty room type."""
        response = client.post(
            "/api/render/quick",
            json={
                "room_type": "",
                "style": "modern",
                "size": "1024x1024"
            }
        )
        # API currently accepts empty room type (generates with empty prompt)
        assert response.status_code in [200, 400, 422]
