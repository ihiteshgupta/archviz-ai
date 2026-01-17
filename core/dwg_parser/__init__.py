"""DWG/DXF Parser Module

This module handles parsing of AutoCAD DWG and DXF files,
extracting architectural elements like walls, doors, windows, and rooms.
"""

from .parser import DWGParser, FloorPlan
from .elements import Wall, Door, Window, Room
from .converter import convert_dwg_to_dxf
from .room_classifier import (
    RoomClassifier,
    RoomContext,
    RoomClassification,
    FIXTURE_PATTERNS,
    ROOM_TYPES,
)

__all__ = [
    "DWGParser",
    "FloorPlan",
    "Wall",
    "Door",
    "Window",
    "Room",
    "convert_dwg_to_dxf",
    "RoomClassifier",
    "RoomContext",
    "RoomClassification",
    "FIXTURE_PATTERNS",
    "ROOM_TYPES",
]
