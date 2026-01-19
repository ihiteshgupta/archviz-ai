"""3D model generation module for ArchViz AI.

This module converts parsed FloorPlan elements (walls, doors, windows, rooms)
into 3D meshes exportable as glTF and OBJ formats.

Usage:
    from core.model_gen import ModelGenerator

    generator = ModelGenerator()
    scene = generator.generate(floor_plan)
    scene.export_gltf("output/model.glb")
    scene.export_obj("output/model.obj")
"""

from .exporter import SceneExporter, export_scene
from .extruder import FloorCeilingExtruder, WallExtruder
from .furniture_library import FURNITURE_DEFAULTS, FurnitureLibrary
from .furniture_placer import FurniturePlacer
from .generator import GeneratorConfig, ModelGenerator
from .openings import OpeningProcessor
from .types import Mesh3D, Scene3D

__all__ = [
    # Main API
    "ModelGenerator",
    "GeneratorConfig",
    "Scene3D",
    "Mesh3D",
    # Export utilities
    "SceneExporter",
    "export_scene",
    # Sub-processors (for advanced usage)
    "WallExtruder",
    "FloorCeilingExtruder",
    "OpeningProcessor",
    # AI-guided placement
    "FurniturePlacer",
    # Furniture assets
    "FurnitureLibrary",
    "FURNITURE_DEFAULTS",
]
