"""Tests for the core materials system."""

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.dwg_parser.elements import Room
from core.dwg_parser.parser import FloorPlan, FloorPlanMetadata
from core.materials import (
    INDUSTRIAL,
    MINIMALIST,
    MODERN,
    PRESETS,
    RUSTIC,
    SCANDINAVIAN,
    TRADITIONAL,
    Material,
    MaterialAssignment,
    MaterialFetcher,
    MaterialLibrary,
    MaterialSuggester,
    PresetName,
    StylePreset,
    get_preset,
    list_presets,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_material():
    """Create a sample material for testing."""
    return Material(
        id="test_wood",
        name="Test Wood",
        category="wood",
        base_color=(0.7, 0.5, 0.3),
        roughness=0.6,
        metallic=0.0,
        tags=["warm", "natural"],
        suitable_for=["floor", "wall"],
        room_affinity=["living", "bedroom"],
        styles=["modern", "rustic"],
        source="bundled",
    )


@pytest.fixture
def sample_room():
    """Create a sample room for testing."""
    return Room(
        id="room1",
        name="Living Room",
        polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
        floor_level=0,
        ceiling_height=3.0,
        room_type="living",
    )


@pytest.fixture
def sample_floor_plan(sample_room):
    """Create a sample floor plan for testing."""
    return FloorPlan(
        metadata=FloorPlanMetadata(filename="test.dxf"),
        rooms=[sample_room],
    )


@pytest.fixture
def temp_library_dir():
    """Create a temporary directory with a library.json file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        library_data = {
            "version": "1.0",
            "materials": [
                {
                    "id": "wood_oak",
                    "name": "Oak Wood",
                    "category": "wood",
                    "base_color": [0.7, 0.5, 0.3],
                    "roughness": 0.6,
                    "metallic": 0.0,
                    "tags": ["warm", "natural"],
                    "suitable_for": ["floor", "wall"],
                    "room_affinity": ["living", "bedroom"],
                    "styles": ["modern", "scandinavian"],
                },
                {
                    "id": "paint_white",
                    "name": "White Paint",
                    "category": "paint",
                    "base_color": [0.98, 0.98, 0.98],
                    "roughness": 0.5,
                    "metallic": 0.0,
                    "tags": ["clean", "neutral"],
                    "suitable_for": ["wall", "ceiling"],
                    "room_affinity": ["living", "bedroom", "kitchen"],
                    "styles": ["modern", "minimalist", "scandinavian"],
                },
                {
                    "id": "ceramic_tile",
                    "name": "White Ceramic Tile",
                    "category": "ceramic",
                    "base_color": [0.95, 0.95, 0.95],
                    "roughness": 0.3,
                    "metallic": 0.0,
                    "tags": ["clean", "glossy"],
                    "suitable_for": ["floor", "wall"],
                    "room_affinity": ["bathroom", "kitchen"],
                    "styles": ["modern", "minimalist"],
                },
            ],
        }

        library_path = os.path.join(tmpdir, "library.json")
        with open(library_path, "w") as f:
            json.dump(library_data, f)

        yield tmpdir


# ============================================================================
# Material Tests
# ============================================================================


class TestMaterial:
    """Tests for Material dataclass."""

    def test_create_material(self):
        """Test creating a material with default values."""
        material = Material()
        assert material.id is not None
        assert material.category == "generic"
        assert material.roughness == 0.5

    def test_create_material_with_values(self, sample_material):
        """Test creating a material with custom values."""
        assert sample_material.id == "test_wood"
        assert sample_material.name == "Test Wood"
        assert sample_material.category == "wood"
        assert sample_material.base_color == (0.7, 0.5, 0.3)

    def test_to_dict(self, sample_material):
        """Test converting material to dictionary."""
        data = sample_material.to_dict()
        assert data["id"] == "test_wood"
        assert data["name"] == "Test Wood"
        assert data["category"] == "wood"
        assert data["base_color"] == [0.7, 0.5, 0.3]
        assert data["tags"] == ["warm", "natural"]

    def test_from_dict(self):
        """Test creating material from dictionary."""
        data = {
            "id": "test_stone",
            "name": "Test Stone",
            "category": "stone",
            "base_color": [0.5, 0.5, 0.5],
            "roughness": 0.7,
            "tags": ["natural"],
        }
        material = Material.from_dict(data)
        assert material.id == "test_stone"
        assert material.category == "stone"
        assert material.roughness == 0.7

    def test_matches_style(self, sample_material):
        """Test style matching."""
        assert sample_material.matches_style("modern")
        assert sample_material.matches_style("MODERN")
        assert sample_material.matches_style("rustic")
        assert not sample_material.matches_style("industrial")

    def test_matches_room(self, sample_material):
        """Test room matching."""
        assert sample_material.matches_room("living")
        assert sample_material.matches_room("bedroom")
        assert not sample_material.matches_room("bathroom")

    def test_suitable_for_surface(self, sample_material):
        """Test surface suitability."""
        assert sample_material.suitable_for_surface("floor")
        assert sample_material.suitable_for_surface("wall")
        assert not sample_material.suitable_for_surface("ceiling")


class TestMaterialAssignment:
    """Tests for MaterialAssignment dataclass."""

    def test_create_assignment(self):
        """Test creating a material assignment."""
        assignment = MaterialAssignment(
            surface_id="room1_floor",
            material_id="wood_oak",
            room_id="room1",
            surface_type="floor",
        )
        assert assignment.surface_id == "room1_floor"
        assert assignment.material_id == "wood_oak"

    def test_to_dict(self):
        """Test converting assignment to dictionary."""
        assignment = MaterialAssignment(
            surface_id="room1_floor",
            material_id="wood_oak",
        )
        data = assignment.to_dict()
        assert data["surface_id"] == "room1_floor"
        assert data["material_id"] == "wood_oak"

    def test_from_dict(self):
        """Test creating assignment from dictionary."""
        data = {
            "surface_id": "room1_wall",
            "material_id": "paint_white",
            "room_id": "room1",
            "surface_type": "wall",
        }
        assignment = MaterialAssignment.from_dict(data)
        assert assignment.surface_id == "room1_wall"
        assert assignment.room_id == "room1"


# ============================================================================
# StylePreset Tests
# ============================================================================


class TestStylePreset:
    """Tests for StylePreset."""

    def test_preset_attributes(self):
        """Test preset has required attributes."""
        assert MODERN.id == "modern"
        assert MODERN.name == "Modern"
        assert "neutral" in MODERN.color_palette or "white" in MODERN.color_palette
        assert MODERN.texture_preference == "minimal"

    def test_all_presets_exist(self):
        """Test all 6 presets are defined."""
        assert len(PRESETS) == 6
        assert "modern" in PRESETS
        assert "rustic" in PRESETS
        assert "industrial" in PRESETS
        assert "scandinavian" in PRESETS
        assert "traditional" in PRESETS
        assert "minimalist" in PRESETS

    def test_get_preset(self):
        """Test getting preset by name."""
        preset = get_preset("modern")
        assert preset.id == "modern"

        preset = get_preset("MODERN")  # Case insensitive
        assert preset.id == "modern"

    def test_get_preset_invalid(self):
        """Test getting invalid preset raises error."""
        with pytest.raises(ValueError):
            get_preset("invalid_preset")

    def test_list_presets(self):
        """Test listing all presets."""
        presets = list_presets()
        assert len(presets) == 6
        assert all(isinstance(p, StylePreset) for p in presets)

    def test_preset_to_dict(self):
        """Test converting preset to dictionary."""
        data = MODERN.to_dict()
        assert data["id"] == "modern"
        assert data["name"] == "Modern"
        assert "prompt_description" in data


# ============================================================================
# MaterialLibrary Tests
# ============================================================================


class TestMaterialLibrary:
    """Tests for MaterialLibrary."""

    def test_create_empty_library(self):
        """Test creating library with no materials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            library = MaterialLibrary(data_dir=tmpdir)
            assert library.count() == 0

    def test_load_bundled_materials(self, temp_library_dir):
        """Test loading materials from library.json."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        assert library.count() == 3

    def test_get_material(self, temp_library_dir):
        """Test getting a material by ID."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        material = library.get("wood_oak")
        assert material is not None
        assert material.name == "Oak Wood"

    def test_get_nonexistent_material(self, temp_library_dir):
        """Test getting a nonexistent material returns None."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        material = library.get("nonexistent")
        assert material is None

    def test_add_material(self, temp_library_dir, sample_material):
        """Test adding a material to the library."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        initial_count = library.count()
        library.add(sample_material)
        assert library.count() == initial_count + 1
        assert library.get("test_wood") is not None

    def test_remove_material(self, temp_library_dir):
        """Test removing a material from the library."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        assert library.remove("wood_oak")
        assert library.get("wood_oak") is None

    def test_search_by_category(self, temp_library_dir):
        """Test searching materials by category."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        results = library.search(category="wood")
        assert len(results) == 1
        assert results[0].id == "wood_oak"

    def test_search_by_suitable_for(self, temp_library_dir):
        """Test searching materials by surface type."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        results = library.search(suitable_for="floor")
        assert len(results) == 2  # wood_oak and ceramic_tile

    def test_search_by_style(self, temp_library_dir):
        """Test searching materials by style."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        results = library.search(style="minimalist")
        assert len(results) == 2  # paint_white and ceramic_tile

    def test_search_by_room_type(self, temp_library_dir):
        """Test searching materials by room type."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        results = library.search(room_type="bathroom")
        assert len(results) == 1  # ceramic_tile

    def test_search_by_query(self, temp_library_dir):
        """Test free text search."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        results = library.search(query="oak")
        assert len(results) == 1
        assert results[0].id == "wood_oak"

    def test_search_combined_filters(self, temp_library_dir):
        """Test search with multiple filters."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        results = library.search(suitable_for="wall", style="modern")
        assert len(results) >= 1

    def test_list_categories(self, temp_library_dir):
        """Test listing all categories."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        categories = library.list_categories()
        assert "wood" in categories
        assert "paint" in categories
        assert "ceramic" in categories

    def test_all_materials(self, temp_library_dir):
        """Test getting all materials."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        all_materials = library.all()
        assert len(all_materials) == 3


# ============================================================================
# MaterialFetcher Tests
# ============================================================================


class TestMaterialFetcher:
    """Tests for MaterialFetcher."""

    def test_create_fetcher(self):
        """Test creating a fetcher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = MaterialFetcher(cache_dir=tmpdir, resolution="1K")
            assert fetcher.resolution == "1K"

    def test_is_cached_false(self):
        """Test is_cached returns False for uncached material."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = MaterialFetcher(cache_dir=tmpdir)
            assert not fetcher.is_cached("nonexistent_asset")

    def test_list_cached_empty(self):
        """Test list_cached returns empty for new cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = MaterialFetcher(cache_dir=tmpdir)
            assert fetcher.list_cached() == []

    def test_clear_cache(self):
        """Test clearing the cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = MaterialFetcher(cache_dir=tmpdir)

            # Create some cached items
            cache_path = fetcher.cache_dir / "test_asset"
            cache_path.mkdir(parents=True)
            (cache_path / "material.json").write_text("{}")

            assert fetcher.is_cached("test_asset")

            count = fetcher.clear_cache()
            assert count == 1
            assert not fetcher.is_cached("test_asset")


# ============================================================================
# MaterialSuggester Tests
# ============================================================================


class TestMaterialSuggester:
    """Tests for MaterialSuggester."""

    def test_create_suggester(self, temp_library_dir):
        """Test creating a suggester."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        suggester = MaterialSuggester(library)
        assert suggester.library == library
        assert suggester.openai is None

    @pytest.mark.asyncio
    async def test_suggest_for_room_defaults(self, temp_library_dir, sample_room):
        """Test suggesting materials for a room using defaults."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        suggester = MaterialSuggester(library)

        result = await suggester.suggest_for_room(sample_room, MODERN)

        assert "floor" in result
        assert "wall" in result
        assert "ceiling" in result
        assert isinstance(result["floor"], Material)

    @pytest.mark.asyncio
    async def test_suggest_for_floor_plan(self, temp_library_dir, sample_floor_plan):
        """Test suggesting materials for a floor plan."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        suggester = MaterialSuggester(library)

        result = await suggester.suggest(sample_floor_plan, MODERN)

        assert len(result) > 0
        assert all(isinstance(a, MaterialAssignment) for a in result.values())

    @pytest.mark.asyncio
    async def test_suggest_with_style_string(self, temp_library_dir, sample_room):
        """Test suggesting materials with style as string."""
        library = MaterialLibrary(data_dir=temp_library_dir)
        suggester = MaterialSuggester(library)

        result = await suggester.suggest_for_room(sample_room, "modern")

        assert "floor" in result
        assert isinstance(result["floor"], Material)

    @pytest.mark.asyncio
    async def test_suggest_with_ai_mocked(self, temp_library_dir, sample_room):
        """Test AI suggestion with mocked OpenAI service."""
        library = MaterialLibrary(data_dir=temp_library_dir)

        mock_openai = MagicMock()
        mock_openai.chat_completion = AsyncMock(
            return_value='{"floor": "wood_oak", "wall": "paint_white", "ceiling": "paint_white"}'
        )

        suggester = MaterialSuggester(library, openai_service=mock_openai)

        result = await suggester.suggest_for_room(sample_room, MODERN)

        assert result["floor"].id == "wood_oak"
        assert result["wall"].id == "paint_white"

    @pytest.mark.asyncio
    async def test_suggest_ai_fallback_on_error(self, temp_library_dir, sample_room):
        """Test fallback to defaults when AI fails."""
        library = MaterialLibrary(data_dir=temp_library_dir)

        mock_openai = MagicMock()
        mock_openai.chat_completion = AsyncMock(side_effect=Exception("API Error"))

        suggester = MaterialSuggester(library, openai_service=mock_openai)

        result = await suggester.suggest_for_room(sample_room, MODERN)

        # Should still return valid materials via fallback
        assert "floor" in result
        assert "wall" in result
        assert isinstance(result["floor"], Material)

    @pytest.mark.asyncio
    async def test_suggest_ai_invalid_json_fallback(self, temp_library_dir, sample_room):
        """Test fallback when AI returns invalid JSON."""
        library = MaterialLibrary(data_dir=temp_library_dir)

        mock_openai = MagicMock()
        mock_openai.chat_completion = AsyncMock(return_value="not valid json")

        suggester = MaterialSuggester(library, openai_service=mock_openai)

        result = await suggester.suggest_for_room(sample_room, MODERN)

        # Should still return valid materials via fallback
        assert "floor" in result
        assert isinstance(result["floor"], Material)


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for the materials system."""

    def test_full_library_load(self):
        """Test loading the actual bundled library."""
        # Use the real library.json from the project
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "materials",
        )

        if os.path.exists(os.path.join(data_dir, "library.json")):
            library = MaterialLibrary(data_dir=data_dir)
            assert library.count() > 0

            # Test we can search the real library
            wood_materials = library.search(category="wood")
            assert len(wood_materials) > 0

    @pytest.mark.asyncio
    async def test_suggester_with_real_library(self, sample_floor_plan):
        """Test suggester with the real library."""
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "materials",
        )

        if os.path.exists(os.path.join(data_dir, "library.json")):
            library = MaterialLibrary(data_dir=data_dir)
            suggester = MaterialSuggester(library)

            result = await suggester.suggest(sample_floor_plan, MODERN)
            assert len(result) > 0

    def test_preset_material_affinity(self):
        """Test that presets have valid material affinities."""
        for preset in list_presets():
            assert len(preset.material_affinity) > 0
            assert preset.texture_preference in ["minimal", "natural", "moderate", "heavy"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
