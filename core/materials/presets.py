"""Style presets for material suggestions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


@dataclass
class StylePreset:
    """Defines style characteristics for AI material selection."""

    id: str
    name: str
    description: str

    # Guidance for AI
    color_palette: List[str] = field(default_factory=list)  # ["neutral", "warm"]
    texture_preference: str = "moderate"  # "minimal", "natural", "heavy"
    material_affinity: List[str] = field(default_factory=list)  # Preferred categories
    avoid_materials: List[str] = field(default_factory=list)  # Categories to avoid

    # Prompt snippet for LLM
    prompt_description: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color_palette": self.color_palette,
            "texture_preference": self.texture_preference,
            "material_affinity": self.material_affinity,
            "avoid_materials": self.avoid_materials,
            "prompt_description": self.prompt_description,
        }


# Built-in style presets
MODERN = StylePreset(
    id="modern",
    name="Modern",
    description="Clean lines, neutral palette, minimal ornamentation",
    color_palette=["white", "gray", "black", "natural wood"],
    texture_preference="minimal",
    material_affinity=["concrete", "wood", "metal", "glass"],
    avoid_materials=["ornate", "busy patterns", "heavy textures"],
    prompt_description=(
        "Modern style: clean lines, neutral colors (white, gray, black), "
        "smooth surfaces, natural wood accents, minimal texture, "
        "polished concrete or light hardwood floors"
    ),
)

RUSTIC = StylePreset(
    id="rustic",
    name="Rustic",
    description="Natural materials, warm earth tones, cozy textures",
    color_palette=["brown", "tan", "cream", "forest green", "rust"],
    texture_preference="natural",
    material_affinity=["wood", "stone", "brick", "fabric"],
    avoid_materials=["metal", "glass", "high-gloss"],
    prompt_description=(
        "Rustic style: natural wood with visible grain, stone accents, "
        "warm earth tones (brown, tan, cream), cozy textures, "
        "reclaimed wood floors, exposed stone walls"
    ),
)

INDUSTRIAL = StylePreset(
    id="industrial",
    name="Industrial",
    description="Raw materials, exposed elements, urban aesthetic",
    color_palette=["gray", "black", "rust", "raw concrete"],
    texture_preference="heavy",
    material_affinity=["concrete", "metal", "brick", "wood"],
    avoid_materials=["ornate", "delicate patterns", "pastel colors"],
    prompt_description=(
        "Industrial style: exposed concrete, metal fixtures, "
        "raw and unfinished surfaces, gray and black palette, "
        "polished concrete floors, exposed brick walls"
    ),
)

SCANDINAVIAN = StylePreset(
    id="scandinavian",
    name="Scandinavian",
    description="Light, airy, functional with natural elements",
    color_palette=["white", "light gray", "pale blue", "light wood"],
    texture_preference="minimal",
    material_affinity=["wood", "fabric", "ceramic"],
    avoid_materials=["dark colors", "heavy textures", "ornate patterns"],
    prompt_description=(
        "Scandinavian style: light and airy spaces, white walls, "
        "light wood (oak, birch, pine), minimal decoration, "
        "functional design, pale neutral colors, cozy textiles"
    ),
)

TRADITIONAL = StylePreset(
    id="traditional",
    name="Traditional",
    description="Classic elegance, rich materials, timeless design",
    color_palette=["cream", "burgundy", "navy", "forest green", "gold accents"],
    texture_preference="natural",
    material_affinity=["wood", "marble", "fabric", "ceramic"],
    avoid_materials=["industrial", "ultra-modern", "raw concrete"],
    prompt_description=(
        "Traditional style: rich wood tones (mahogany, cherry, walnut), "
        "classic patterns, elegant marble, warm colors, "
        "hardwood floors, crown molding, refined materials"
    ),
)

MINIMALIST = StylePreset(
    id="minimalist",
    name="Minimalist",
    description="Ultra-clean, monochrome, essential elements only",
    color_palette=["white", "black", "gray"],
    texture_preference="minimal",
    material_affinity=["concrete", "glass", "metal"],
    avoid_materials=["patterns", "heavy textures", "ornate details"],
    prompt_description=(
        "Minimalist style: ultra-clean surfaces, monochrome palette, "
        "no unnecessary decoration, white or light gray walls, "
        "smooth polished floors, hidden storage, essential elements only"
    ),
)


# Preset registry
PRESETS: Dict[str, StylePreset] = {
    "modern": MODERN,
    "rustic": RUSTIC,
    "industrial": INDUSTRIAL,
    "scandinavian": SCANDINAVIAN,
    "traditional": TRADITIONAL,
    "minimalist": MINIMALIST,
}


class PresetName(str, Enum):
    """Enum for preset names."""

    MODERN = "modern"
    RUSTIC = "rustic"
    INDUSTRIAL = "industrial"
    SCANDINAVIAN = "scandinavian"
    TRADITIONAL = "traditional"
    MINIMALIST = "minimalist"


def get_preset(name: str) -> StylePreset:
    """Get a style preset by name."""
    name_lower = name.lower()
    if name_lower not in PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(PRESETS.keys())}")
    return PRESETS[name_lower]


def list_presets() -> List[StylePreset]:
    """Get all available presets."""
    return list(PRESETS.values())
