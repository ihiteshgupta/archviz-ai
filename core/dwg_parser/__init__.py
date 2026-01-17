"""DWG/DXF Parser Module

This module handles parsing of AutoCAD DWG and DXF files,
extracting architectural elements like walls, doors, windows, and rooms.
"""

from .converter import convert_dwg_to_dxf
from .elements import Door, Room, Wall, Window
from .parser import DWGParser, FloorPlan
from .room_classifier import (
    FIXTURE_PATTERNS,
    ROOM_TYPES,
    RoomClassification,
    RoomClassifier,
    RoomContext,
)
from .wall_graph import WallGraph

__all__ = [
    "DWGParser",
    "FloorPlan",
    "Wall",
    "Door",
    "Window",
    "Room",
    "convert_dwg_to_dxf",
    "WallGraph",
    "RoomClassifier",
    "RoomContext",
    "RoomClassification",
    "FIXTURE_PATTERNS",
    "ROOM_TYPES",
]
