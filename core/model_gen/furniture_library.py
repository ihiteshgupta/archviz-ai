# core/model_gen/furniture_library.py
"""Furniture asset library for 3D model placement."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import trimesh


logger = logging.getLogger(__name__)


# Default furniture dimensions (meters) for placeholder generation
FURNITURE_DEFAULTS: dict[str, dict[str, float]] = {
    "armchair": {"width": 0.9, "depth": 0.9, "height": 0.85},
    "bed_king": {"width": 1.9, "depth": 2.0, "height": 0.5},
    "bed_queen": {"width": 1.6, "depth": 2.0, "height": 0.5},
    "bed_single": {"width": 0.9, "depth": 2.0, "height": 0.5},
    "bookshelf": {"width": 0.8, "depth": 0.3, "height": 1.8},
    "chair": {"width": 0.5, "depth": 0.5, "height": 0.9},
    "coffee_table": {"width": 1.2, "depth": 0.6, "height": 0.45},
    "desk": {"width": 1.2, "depth": 0.6, "height": 0.75},
    "dining_chair": {"width": 0.45, "depth": 0.45, "height": 0.9},
    "dining_table": {"width": 1.6, "depth": 0.9, "height": 0.75},
    "dresser": {"width": 1.2, "depth": 0.5, "height": 0.9},
    "nightstand": {"width": 0.5, "depth": 0.4, "height": 0.6},
    "sofa_3seat": {"width": 2.2, "depth": 0.9, "height": 0.85},
    "wardrobe": {"width": 1.8, "depth": 0.6, "height": 2.2},
}


class FurnitureLibrary:
    """Manages furniture 3D assets.

    This library provides access to furniture 3D models for room furnishing.
    For MVP, it generates simple box placeholders with correct dimensions
    when actual 3D models aren't available. This allows the pipeline to work
    without requiring actual furniture model assets.

    Usage:
        library = FurnitureLibrary()

        # List available furniture types
        types = library.list_types()  # ['armchair', 'bed_king', 'bed_queen', ...]

        # Get a furniture mesh
        mesh = library.get_asset("bed_queen")  # Returns trimesh.Trimesh

        # Get dimensions without creating mesh
        dims = library.get_dimensions("bed_queen")  # {'width': 1.6, 'depth': 2.0, 'height': 0.5}
    """

    def __init__(self, assets_dir: str | Path | None = None):
        """Initialize the FurnitureLibrary.

        Args:
            assets_dir: Optional path to directory containing .glb furniture assets.
                       If not provided, defaults to assets/furniture/ relative to
                       the project root.
        """
        if assets_dir:
            self.assets_dir = Path(assets_dir)
        else:
            # Default to assets/furniture relative to project root
            self.assets_dir = Path(__file__).parent.parent.parent / "assets" / "furniture"

    def list_types(self) -> list[str]:
        """List all available furniture types.

        Returns a sorted list of furniture type names. This includes both
        built-in placeholder types from FURNITURE_DEFAULTS and any custom
        .glb assets found in the assets directory.

        Returns:
            Sorted list of furniture type names.
        """
        types = set(FURNITURE_DEFAULTS.keys())

        # Add any custom assets from directory
        if self.assets_dir.exists():
            for f in self.assets_dir.glob("*.glb"):
                types.add(f.stem)

        return sorted(types)

    def get_asset(self, furniture_type: str) -> trimesh.Trimesh | None:
        """Get furniture mesh by type.

        Attempts to load from .glb file first, falls back to generating
        a placeholder box if the type is known but no file exists.

        Args:
            furniture_type: The type of furniture to retrieve (e.g., "bed_queen").

        Returns:
            A trimesh.Trimesh object representing the furniture, or None if
            the furniture type is not recognized.
        """
        # Try to load from file first
        asset_path = self.assets_dir / f"{furniture_type}.glb"
        if asset_path.exists():
            try:
                scene = trimesh.load(asset_path)
                # Handle both Scene and Trimesh returns
                if isinstance(scene, trimesh.Scene):
                    # Merge all geometries in scene
                    meshes = list(scene.geometry.values())
                    if meshes:
                        return trimesh.util.concatenate(meshes)
                    return None
                return scene
            except Exception as e:
                logger.warning(f"Failed to load asset {asset_path}: {e}")
                # Fall through to placeholder generation

        # Generate placeholder box if we have dimensions
        if furniture_type in FURNITURE_DEFAULTS:
            dims = FURNITURE_DEFAULTS[furniture_type]
            return self._create_placeholder(dims)

        return None

    def get_dimensions(self, furniture_type: str) -> dict[str, float] | None:
        """Get dimensions for a furniture type without creating a mesh.

        Args:
            furniture_type: The type of furniture to get dimensions for.

        Returns:
            Dictionary with 'width', 'depth', and 'height' keys (in meters),
            or None if the furniture type is not recognized.
        """
        if furniture_type in FURNITURE_DEFAULTS:
            return FURNITURE_DEFAULTS[furniture_type].copy()
        return None

    def _create_placeholder(self, dims: dict[str, float]) -> trimesh.Trimesh:
        """Create a simple box placeholder for furniture.

        The box is created with the specified dimensions and positioned so that
        its bottom face is at y=0 (floor level).

        Args:
            dims: Dictionary with 'width', 'depth', and 'height' keys in meters.

        Returns:
            A trimesh.Trimesh box representing the furniture placeholder.
        """
        # Create box centered at origin
        box = trimesh.creation.box(
            extents=[dims["width"], dims["height"], dims["depth"]]
        )
        # Move so bottom is at y=0 (floor level)
        box.apply_translation([0, dims["height"] / 2, 0])
        return box
