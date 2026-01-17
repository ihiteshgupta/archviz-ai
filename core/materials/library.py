"""Material library for managing bundled and external materials."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from .types import Material


class MaterialLibrary:
    """Manages bundled and external materials with search/filter capabilities."""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the material library.

        Args:
            data_dir: Path to materials data directory. Defaults to data/materials.
        """
        if data_dir is None:
            # Default to data/materials relative to project root
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "materials",
            )

        self.data_dir = Path(data_dir)
        self.materials: Dict[str, Material] = {}
        self._load_bundled()

    def _load_bundled(self) -> None:
        """Load bundled materials from library.json."""
        library_path = self.data_dir / "library.json"

        if not library_path.exists():
            # No bundled materials yet
            return

        try:
            with open(library_path, "r") as f:
                data = json.load(f)

            for mat_data in data.get("materials", []):
                material = Material.from_dict(mat_data)
                self.materials[material.id] = material
        except (json.JSONDecodeError, IOError) as e:
            # Log error but don't fail - library can work without bundled materials
            print(f"Warning: Failed to load materials library: {e}")

    def get(self, material_id: str) -> Optional[Material]:
        """Get a material by ID."""
        return self.materials.get(material_id)

    def add(self, material: Material) -> None:
        """Add a material to the library."""
        self.materials[material.id] = material

    def add_external(self, material: Material) -> None:
        """Add an externally fetched material to the library."""
        material.source = "external"
        self.materials[material.id] = material

    def remove(self, material_id: str) -> bool:
        """Remove a material from the library."""
        if material_id in self.materials:
            del self.materials[material_id]
            return True
        return False

    def search(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        suitable_for: Optional[str] = None,
        style: Optional[str] = None,
        room_type: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Material]:
        """
        Search materials with various filters.

        Args:
            category: Filter by category (wood, stone, etc.)
            tags: Filter by tags (must match at least one)
            suitable_for: Filter by surface type (floor, wall, ceiling)
            style: Filter by style (modern, rustic, etc.)
            room_type: Filter by room affinity (kitchen, bedroom, etc.)
            query: Free text search in name and tags

        Returns:
            List of matching materials
        """
        results = list(self.materials.values())

        if category:
            results = [m for m in results if m.category.lower() == category.lower()]

        if tags:
            tags_lower = [t.lower() for t in tags]
            results = [
                m
                for m in results
                if any(t.lower() in tags_lower for t in m.tags)
            ]

        if suitable_for:
            results = [m for m in results if m.suitable_for_surface(suitable_for)]

        if style:
            results = [m for m in results if m.matches_style(style)]

        if room_type:
            results = [m for m in results if m.matches_room(room_type)]

        if query:
            query_lower = query.lower()
            results = [
                m
                for m in results
                if query_lower in m.name.lower()
                or query_lower in m.id.lower()
                or any(query_lower in t.lower() for t in m.tags)
            ]

        return results

    def list_categories(self) -> List[str]:
        """Get all unique categories in the library."""
        categories = set()
        for material in self.materials.values():
            categories.add(material.category)
        return sorted(categories)

    def list_by_category(self, category: str) -> List[Material]:
        """Get all materials in a category."""
        return self.search(category=category)

    def get_for_surface(
        self, surface_type: str, style: Optional[str] = None
    ) -> List[Material]:
        """Get materials suitable for a surface type, optionally filtered by style."""
        return self.search(suitable_for=surface_type, style=style)

    def get_for_room(
        self, room_type: str, surface_type: Optional[str] = None
    ) -> List[Material]:
        """Get materials suitable for a room type, optionally filtered by surface."""
        return self.search(room_type=room_type, suitable_for=surface_type)

    def count(self) -> int:
        """Get total number of materials in library."""
        return len(self.materials)

    def all(self) -> List[Material]:
        """Get all materials in the library."""
        return list(self.materials.values())

    def save_library(self, path: Optional[str] = None) -> None:
        """Save the library to JSON file."""
        if path is None:
            path = str(self.data_dir / "library.json")

        data = {
            "version": "1.0",
            "materials": [m.to_dict() for m in self.materials.values()],
        }

        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def get_default_for_surface(self, surface_type: str) -> Optional[Material]:
        """Get a default material for a surface type."""
        defaults = {
            "floor": "wood_oak_natural",
            "wall": "paint_white",
            "ceiling": "paint_white",
            "door_frame": "wood_oak_natural",
            "door_panel": "wood_oak_natural",
            "window_frame": "metal_aluminum",
            "window_glass": "glass_clear",
        }

        default_id = defaults.get(surface_type)
        if default_id and default_id in self.materials:
            return self.materials[default_id]

        # Fall back to first suitable material
        suitable = self.search(suitable_for=surface_type)
        return suitable[0] if suitable else None
