# tests/test_furniture_library.py
"""Tests for furniture asset library."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path

from core.model_gen.furniture_library import FurnitureLibrary, FURNITURE_DEFAULTS


class TestFurnitureLibrary:
    """Tests for furniture asset library."""

    def test_lists_available_furniture_types(self):
        """Should list all available furniture types."""
        library = FurnitureLibrary()
        types = library.list_types()

        assert isinstance(types, list)
        assert len(types) > 0
        assert "bed_queen" in types or "bed" in types

    def test_returns_none_for_missing_asset(self):
        """Should return None for non-existent furniture type."""
        library = FurnitureLibrary()
        asset = library.get_asset("nonexistent_furniture_xyz")

        assert asset is None

    def test_get_asset_returns_trimesh_for_known_type(self):
        """Should return a trimesh object for known furniture types."""
        import trimesh

        library = FurnitureLibrary()
        asset = library.get_asset("bed_queen")

        assert asset is not None
        assert isinstance(asset, trimesh.Trimesh)

    def test_placeholder_has_correct_dimensions(self):
        """Placeholder meshes should have dimensions matching FURNITURE_DEFAULTS."""
        library = FurnitureLibrary()

        for furniture_type, expected_dims in FURNITURE_DEFAULTS.items():
            asset = library.get_asset(furniture_type)
            assert asset is not None, f"Missing asset for {furniture_type}"

            # Get bounding box extents
            bounds = asset.bounds
            actual_width = bounds[1][0] - bounds[0][0]
            actual_height = bounds[1][1] - bounds[0][1]
            actual_depth = bounds[1][2] - bounds[0][2]

            # Check dimensions match (with floating point tolerance)
            assert abs(actual_width - expected_dims["width"]) < 0.01, (
                f"{furniture_type} width: expected {expected_dims['width']}, got {actual_width}"
            )
            assert abs(actual_height - expected_dims["height"]) < 0.01, (
                f"{furniture_type} height: expected {expected_dims['height']}, got {actual_height}"
            )
            assert abs(actual_depth - expected_dims["depth"]) < 0.01, (
                f"{furniture_type} depth: expected {expected_dims['depth']}, got {actual_depth}"
            )

    def test_placeholder_bottom_at_floor_level(self):
        """Placeholder meshes should have their bottom at y=0 (floor level)."""
        library = FurnitureLibrary()
        asset = library.get_asset("bed_queen")

        assert asset is not None
        # Bottom of bounding box should be at y=0
        min_y = asset.bounds[0][1]
        assert abs(min_y) < 0.001, f"Bottom should be at y=0, but is at y={min_y}"

    def test_custom_assets_directory(self):
        """Should accept custom assets directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            library = FurnitureLibrary(assets_dir=tmpdir)
            assert library.assets_dir == Path(tmpdir)

    def test_list_types_includes_custom_glb_files(self):
        """Should include .glb files from assets directory in list_types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy .glb file (just need the file to exist)
            custom_asset = Path(tmpdir) / "custom_table.glb"
            custom_asset.touch()

            library = FurnitureLibrary(assets_dir=tmpdir)
            types = library.list_types()

            assert "custom_table" in types

    def test_list_types_returns_sorted_list(self):
        """Should return sorted list of furniture types."""
        library = FurnitureLibrary()
        types = library.list_types()

        assert types == sorted(types)

    def test_all_default_furniture_types_available(self):
        """All furniture types in FURNITURE_DEFAULTS should be available."""
        library = FurnitureLibrary()
        types = library.list_types()

        for furniture_type in FURNITURE_DEFAULTS:
            assert furniture_type in types, f"Missing type: {furniture_type}"

    def test_get_dimensions_returns_dict_for_known_type(self):
        """Should return dimensions dictionary for known furniture types."""
        library = FurnitureLibrary()
        dims = library.get_dimensions("bed_queen")

        assert dims is not None
        assert "width" in dims
        assert "depth" in dims
        assert "height" in dims
        assert dims["width"] == 1.6
        assert dims["depth"] == 2.0
        assert dims["height"] == 0.5

    def test_get_dimensions_returns_none_for_unknown_type(self):
        """Should return None for unknown furniture types."""
        library = FurnitureLibrary()
        dims = library.get_dimensions("nonexistent_furniture_xyz")

        assert dims is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
