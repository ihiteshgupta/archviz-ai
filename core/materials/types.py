"""Data types for the materials system."""

import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Material:
    """Full PBR material with metadata."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: str = "generic"  # wood, stone, metal, fabric, ceramic, concrete, paint

    # Base properties
    base_color: Tuple[float, float, float] = (0.5, 0.5, 0.5)  # RGB fallback
    roughness: float = 0.5  # 0 = glossy, 1 = rough
    metallic: float = 0.0  # 0 = dielectric, 1 = metal

    # PBR texture paths (relative to materials directory or URLs)
    diffuse_map: Optional[str] = None
    normal_map: Optional[str] = None
    roughness_map: Optional[str] = None
    metallic_map: Optional[str] = None
    ao_map: Optional[str] = None  # Ambient occlusion

    # Metadata for AI suggestions
    tags: List[str] = field(default_factory=list)  # ["warm", "natural", "grain"]
    suitable_for: List[str] = field(default_factory=list)  # ["floor", "furniture", "wall"]
    room_affinity: List[str] = field(default_factory=list)  # ["bedroom", "living", "kitchen"]
    styles: List[str] = field(default_factory=list)  # ["modern", "rustic", "scandinavian"]

    # Source info
    source: str = "bundled"  # "bundled", "ambientcg", "user"
    source_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "base_color": list(self.base_color),
            "roughness": self.roughness,
            "metallic": self.metallic,
            "diffuse_map": self.diffuse_map,
            "normal_map": self.normal_map,
            "roughness_map": self.roughness_map,
            "metallic_map": self.metallic_map,
            "ao_map": self.ao_map,
            "tags": self.tags,
            "suitable_for": self.suitable_for,
            "room_affinity": self.room_affinity,
            "styles": self.styles,
            "source": self.source,
            "source_url": self.source_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Material":
        """Create Material from dictionary."""
        base_color = data.get("base_color", [0.5, 0.5, 0.5])
        if isinstance(base_color, list):
            base_color = tuple(base_color)

        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", ""),
            category=data.get("category", "generic"),
            base_color=base_color,
            roughness=data.get("roughness", 0.5),
            metallic=data.get("metallic", 0.0),
            diffuse_map=data.get("diffuse_map"),
            normal_map=data.get("normal_map"),
            roughness_map=data.get("roughness_map"),
            metallic_map=data.get("metallic_map"),
            ao_map=data.get("ao_map"),
            tags=data.get("tags", []),
            suitable_for=data.get("suitable_for", []),
            room_affinity=data.get("room_affinity", []),
            styles=data.get("styles", []),
            source=data.get("source", "bundled"),
            source_url=data.get("source_url"),
        )

    def matches_style(self, style: str) -> bool:
        """Check if material matches a style."""
        return style.lower() in [s.lower() for s in self.styles]

    def matches_room(self, room_type: str) -> bool:
        """Check if material is suitable for a room type."""
        return room_type.lower() in [r.lower() for r in self.room_affinity]

    def suitable_for_surface(self, surface_type: str) -> bool:
        """Check if material is suitable for a surface type."""
        return surface_type.lower() in [s.lower() for s in self.suitable_for]


@dataclass
class MaterialAssignment:
    """Maps a surface to a material."""

    surface_id: str  # e.g., "room1_floor", "wall_exterior"
    material_id: str  # Reference to Material.id
    room_id: Optional[str] = None
    surface_type: str = "generic"  # "floor", "wall", "ceiling"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "surface_id": self.surface_id,
            "material_id": self.material_id,
            "room_id": self.room_id,
            "surface_type": self.surface_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MaterialAssignment":
        """Create MaterialAssignment from dictionary."""
        return cls(
            surface_id=data.get("surface_id", ""),
            material_id=data.get("material_id", ""),
            room_id=data.get("room_id"),
            surface_type=data.get("surface_type", "generic"),
        )
