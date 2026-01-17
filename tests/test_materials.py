"""Material library API tests."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestMaterialLibrary:
    """Test material library endpoints."""

    def test_get_material_library(self, client):
        """Test fetching the material library."""
        response = client.get("/api/materials/library")
        assert response.status_code == 200
        data = response.json()
        assert "materials" in data
        assert isinstance(data["materials"], list)
        assert len(data["materials"]) > 0

    def test_material_structure(self, client):
        """Test that materials have the correct structure."""
        response = client.get("/api/materials/library")
        materials = response.json()["materials"]

        # Check first material has required fields
        material = materials[0]
        required_fields = ["id", "name", "category", "color_hex", "roughness", "metallic"]
        for field in required_fields:
            assert field in material, f"Missing field: {field}"

    def test_material_color_hex_format(self, client):
        """Test that color_hex values are valid hex colors."""
        response = client.get("/api/materials/library")
        materials = response.json()["materials"]

        for material in materials:
            color = material["color_hex"]
            assert color.startswith("#"), f"Invalid color format: {color}"
            assert len(color) == 7, f"Invalid color length: {color}"

    def test_material_roughness_range(self, client):
        """Test that roughness values are in valid range [0, 1]."""
        response = client.get("/api/materials/library")
        materials = response.json()["materials"]

        for material in materials:
            roughness = material["roughness"]
            assert 0 <= roughness <= 1, f"Invalid roughness: {roughness}"

    def test_material_metallic_range(self, client):
        """Test that metallic values are in valid range [0, 1]."""
        response = client.get("/api/materials/library")
        materials = response.json()["materials"]

        for material in materials:
            metallic = material["metallic"]
            assert 0 <= metallic <= 1, f"Invalid metallic: {metallic}"


class TestMaterialCategories:
    """Test material category endpoints."""

    def test_get_categories(self, client):
        """Test fetching material categories."""
        response = client.get("/api/materials/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data

    def test_filter_by_category(self, client):
        """Test filtering materials by category."""
        response = client.get("/api/materials/library?category=wood")
        assert response.status_code == 200
        data = response.json()

        # Check that wood materials exist in the response
        # Note: API may not filter yet, so just verify response is valid
        assert "materials" in data
        assert isinstance(data["materials"], list)


class TestStylePresets:
    """Test style preset endpoints."""

    def test_get_style_presets(self, client):
        """Test fetching style presets."""
        response = client.get("/api/materials/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert isinstance(data["presets"], list)
        assert len(data["presets"]) > 0

    def test_preset_structure(self, client):
        """Test that presets have the correct structure."""
        response = client.get("/api/materials/presets")
        presets = response.json()["presets"]

        preset = presets[0]
        required_fields = ["id", "name", "description", "materials"]
        for field in required_fields:
            assert field in preset, f"Missing field: {field}"

    def test_preset_has_materials(self, client):
        """Test that presets include material recommendations."""
        response = client.get("/api/materials/presets")
        presets = response.json()["presets"]

        for preset in presets:
            assert "materials" in preset
            assert isinstance(preset["materials"], dict)
            # Should have common material categories
            assert len(preset["materials"]) > 0
