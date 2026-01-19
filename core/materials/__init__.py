"""Materials system for ArchViz AI.

This module provides material management, AI-powered suggestions, and external
material fetching for architectural visualization.

Usage:
    from core.materials import MaterialLibrary, MaterialSuggester, StylePreset

    library = MaterialLibrary()
    suggester = MaterialSuggester(library)

    # Get AI suggestions for a floor plan
    assignments = await suggester.suggest(floor_plan, style="modern")
"""

from .fetcher import MaterialFetcher
from .library import MaterialLibrary
from .presets import (
    INDUSTRIAL,
    MINIMALIST,
    MODERN,
    PRESETS,
    RUSTIC,
    SCANDINAVIAN,
    TRADITIONAL,
    PresetName,
    StylePreset,
    get_preset,
    list_presets,
)
from .suggester import MaterialSuggester
from .texture_generator import TextureGenerator
from .types import Material, MaterialAssignment

__all__ = [
    # Core types
    "Material",
    "MaterialAssignment",
    # Library
    "MaterialLibrary",
    # Fetcher
    "MaterialFetcher",
    # Suggester
    "MaterialSuggester",
    # Texture Generator
    "TextureGenerator",
    # Presets
    "StylePreset",
    "PresetName",
    "get_preset",
    "list_presets",
    "PRESETS",
    # Built-in presets
    "MODERN",
    "RUSTIC",
    "INDUSTRIAL",
    "SCANDINAVIAN",
    "TRADITIONAL",
    "MINIMALIST",
]
