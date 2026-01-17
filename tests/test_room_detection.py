"""Tests for room detection integration in DWGParser."""

import pytest
import tempfile
import os
from pathlib import Path

import ezdxf

from core.dwg_parser.parser import DWGParser, FloorPlan
from core.dwg_parser.elements import Room


def create_simple_dxf(walls_data: list, doors_data: list = None, windows_data: list = None,
                      text_data: list = None, blocks_data: list = None) -> str:
    """Create a temporary DXF file with specified geometry.

    Args:
        walls_data: List of wall segments as [(start_x, start_y), (end_x, end_y)]
        doors_data: List of door positions as (x, y, rotation)
        windows_data: List of window positions as (x, y, rotation)
        text_data: List of text labels as (x, y, text)
        blocks_data: List of block inserts as (x, y, block_name)

    Returns:
        Path to the created DXF file
    """
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Add walls layer
    doc.layers.add("A-WALL")
    for start, end in walls_data:
        msp.add_line(start, end, dxfattribs={"layer": "A-WALL"})

    # Add doors
    if doors_data:
        doc.layers.add("A-DOOR")
        # Create a simple door block if it doesn't exist
        if "DOOR" not in doc.blocks:
            door_block = doc.blocks.new("DOOR")
            door_block.add_line((0, 0), (0.9, 0))  # 0.9m door width
        for x, y, rotation in doors_data:
            msp.add_blockref("DOOR", (x, y), dxfattribs={
                "layer": "A-DOOR",
                "rotation": rotation
            })

    # Add windows
    if windows_data:
        doc.layers.add("A-GLAZ")
        if "WINDOW" not in doc.blocks:
            window_block = doc.blocks.new("WINDOW")
            window_block.add_line((0, 0), (1.2, 0))  # 1.2m window width
        for x, y, rotation in windows_data:
            msp.add_blockref("WINDOW", (x, y), dxfattribs={
                "layer": "A-GLAZ",
                "rotation": rotation
            })

    # Add text labels
    if text_data:
        for x, y, text in text_data:
            msp.add_text(text, dxfattribs={"insert": (x, y)})

    # Add block inserts (fixtures)
    if blocks_data:
        for x, y, block_name in blocks_data:
            if block_name not in doc.blocks:
                b = doc.blocks.new(block_name)
                b.add_circle((0, 0), 0.2)  # Simple placeholder
            msp.add_blockref(block_name, (x, y))

    # Save to temp file
    fd, path = tempfile.mkstemp(suffix=".dxf")
    os.close(fd)
    doc.saveas(path)
    return path


class TestRoomDetectionIntegration:
    """Tests for automatic room detection in DWGParser."""

    def test_parser_accepts_new_parameters(self):
        """Parser should accept snap_tolerance, auto_detect_rooms, and openai_service."""
        parser = DWGParser(
            snap_tolerance=0.1,
            auto_detect_rooms=True,
            openai_service=None
        )
        assert parser.snap_tolerance == 0.1
        assert parser.auto_detect_rooms is True
        assert parser.openai_service is None

    def test_simple_apartment_three_rooms(self):
        """Parser should detect 3 rooms in a simple apartment layout."""
        # Create a simple layout with properly connected walls:
        # +-------+-------+
        # |       |       |
        # | Room1 | Room2 |
        # |       |       |
        # +---+---+-------+
        # |   |           |
        # |   |   Room3   |
        # |   |           |
        # +---+-----------+
        #
        # For WallGraph to find cycles, walls must share endpoints.
        # We need to split boundary walls at intersection points.

        walls = [
            # Bottom boundary split at x=2
            ((0, 0), (2, 0)),
            ((2, 0), (10, 0)),
            # Right boundary split at y=4
            ((10, 0), (10, 4)),
            ((10, 4), (10, 8)),
            # Top boundary split at x=5
            ((10, 8), (5, 8)),
            ((5, 8), (0, 8)),
            # Left boundary split at y=4
            ((0, 8), (0, 4)),
            ((0, 4), (0, 0)),
            # Horizontal divider at y=4 split at x=2 and x=5
            ((0, 4), (2, 4)),
            ((2, 4), (5, 4)),
            ((5, 4), (10, 4)),
            # Vertical divider in top half at x=5
            ((5, 4), (5, 8)),
            # Vertical divider in bottom half at x=2
            ((2, 0), (2, 4)),
        ]

        path = create_simple_dxf(walls)
        try:
            parser = DWGParser(auto_detect_rooms=True, snap_tolerance=0.05)
            floor_plan = parser.parse(path)

            # Should detect 4 rooms total (2 top + 2 bottom)
            # Room1: top-left (0,4) to (5,8) = 20 sq m
            # Room2: top-right (5,4) to (10,8) = 20 sq m
            # Room3: bottom-left (0,0) to (2,4) = 8 sq m
            # Room4: bottom-right (2,0) to (10,4) = 32 sq m
            assert len(floor_plan.rooms) == 4

            # Verify all rooms have valid areas
            for room in floor_plan.rooms:
                assert room.area > 0
        finally:
            os.unlink(path)

    def test_messy_walls_with_gaps(self):
        """Parser should snap wall endpoints within tolerance."""
        # Create walls with small gaps that should be snapped
        walls = [
            ((0, 0), (5, 0)),
            ((5.03, 0), (5.03, 4)),   # Small gap at (5, 0)
            ((5, 4), (0, 4.02)),      # Small gaps
            ((0, 4), (0, 0)),
        ]

        path = create_simple_dxf(walls)
        try:
            parser = DWGParser(auto_detect_rooms=True, snap_tolerance=0.05)
            floor_plan = parser.parse(path)

            # With snapping, should detect 1 room
            assert len(floor_plan.rooms) == 1
        finally:
            os.unlink(path)

    def test_auto_detect_rooms_false_skips_detection(self):
        """When auto_detect_rooms=False, should not run wall-based detection."""
        walls = [
            ((0, 0), (5, 0)),
            ((5, 0), (5, 4)),
            ((5, 4), (0, 4)),
            ((0, 4), (0, 0)),
        ]

        path = create_simple_dxf(walls)
        try:
            parser = DWGParser(auto_detect_rooms=False)
            floor_plan = parser.parse(path)

            # No rooms should be detected from walls when disabled
            # (only rooms on room layers would be extracted)
            assert len(floor_plan.rooms) == 0
        finally:
            os.unlink(path)

    def test_room_types_default_to_unknown_without_ai(self):
        """Without AI service and without fixtures/text, rooms should be 'unknown'."""
        walls = [
            ((0, 0), (5, 0)),
            ((5, 0), (5, 4)),
            ((5, 4), (0, 4)),
            ((0, 4), (0, 0)),
        ]

        path = create_simple_dxf(walls)
        try:
            parser = DWGParser(auto_detect_rooms=True, openai_service=None)
            floor_plan = parser.parse(path)

            assert len(floor_plan.rooms) == 1
            assert floor_plan.rooms[0].room_type == "unknown"
            assert floor_plan.rooms[0].confidence_low is True
        finally:
            os.unlink(path)

    def test_room_classification_from_fixtures(self):
        """Rooms should be classified based on fixture blocks inside them."""
        # Create a simple room with a toilet fixture
        walls = [
            ((0, 0), (3, 0)),
            ((3, 0), (3, 3)),
            ((3, 3), (0, 3)),
            ((0, 3), (0, 0)),
        ]
        blocks = [(1.5, 1.5, "TOILET")]  # Toilet block in center

        path = create_simple_dxf(walls, blocks_data=blocks)
        try:
            parser = DWGParser(auto_detect_rooms=True)
            floor_plan = parser.parse(path)

            assert len(floor_plan.rooms) == 1
            # Should be classified as bathroom due to toilet fixture
            assert floor_plan.rooms[0].room_type == "bathroom"
        finally:
            os.unlink(path)

    def test_room_classification_from_text_label(self):
        """Rooms should be classified based on text labels near centroid."""
        # Create a simple room with a text label
        walls = [
            ((0, 0), (5, 0)),
            ((5, 0), (5, 4)),
            ((5, 4), (0, 4)),
            ((0, 4), (0, 0)),
        ]
        text = [(2.5, 2, "KITCHEN")]  # Text label at room center

        path = create_simple_dxf(walls, text_data=text)
        try:
            parser = DWGParser(auto_detect_rooms=True)
            floor_plan = parser.parse(path)

            assert len(floor_plan.rooms) == 1
            assert floor_plan.rooms[0].room_type == "kitchen"
        finally:
            os.unlink(path)

    def test_door_and_window_count_in_room(self):
        """Parser should count doors and windows inside room boundaries."""
        walls = [
            ((0, 0), (6, 0)),
            ((6, 0), (6, 5)),
            ((6, 5), (0, 5)),
            ((0, 5), (0, 0)),
        ]
        # Add a door and window inside the room boundary
        doors = [(1, 0, 0)]      # Door on bottom wall
        windows = [(3, 5, 0)]    # Window on top wall

        path = create_simple_dxf(walls, doors_data=doors, windows_data=windows)
        try:
            parser = DWGParser(auto_detect_rooms=True)
            floor_plan = parser.parse(path)

            assert len(floor_plan.rooms) == 1
            assert len(floor_plan.doors) == 1
            assert len(floor_plan.windows) == 1
        finally:
            os.unlink(path)

    def test_confidence_low_flag_set_correctly(self):
        """confidence_low should be True when classification confidence < 0.5."""
        walls = [
            ((0, 0), (5, 0)),
            ((5, 0), (5, 4)),
            ((5, 4), (0, 4)),
            ((0, 4), (0, 0)),
        ]

        path = create_simple_dxf(walls)
        try:
            parser = DWGParser(auto_detect_rooms=True, openai_service=None)
            floor_plan = parser.parse(path)

            assert len(floor_plan.rooms) == 1
            # Without fixtures, text, or AI, confidence should be 0
            assert floor_plan.rooms[0].confidence_low is True
        finally:
            os.unlink(path)

    def test_room_to_dict_includes_confidence_low(self):
        """Room.to_dict() should include confidence_low field."""
        room = Room(
            polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
            room_type="bathroom",
            confidence_low=True
        )
        result = room.to_dict()

        assert "confidence_low" in result
        assert result["confidence_low"] is True

    def test_floorplan_json_includes_room_confidence(self):
        """FloorPlan JSON export should include room confidence_low."""
        walls = [
            ((0, 0), (5, 0)),
            ((5, 0), (5, 4)),
            ((5, 4), (0, 4)),
            ((0, 4), (0, 0)),
        ]

        path = create_simple_dxf(walls)
        try:
            parser = DWGParser(auto_detect_rooms=True)
            floor_plan = parser.parse(path)

            json_output = floor_plan.to_json()
            assert "confidence_low" in json_output
        finally:
            os.unlink(path)


class TestEdgeCases:
    """Edge case tests for room detection."""

    def test_no_walls_no_rooms(self):
        """Empty file should result in no rooms."""
        doc = ezdxf.new("R2010")
        fd, path = tempfile.mkstemp(suffix=".dxf")
        os.close(fd)
        doc.saveas(path)

        try:
            parser = DWGParser(auto_detect_rooms=True)
            floor_plan = parser.parse(path)
            assert len(floor_plan.rooms) == 0
        finally:
            os.unlink(path)

    def test_open_walls_no_rooms(self):
        """Unclosed wall configuration should not create rooms."""
        walls = [
            ((0, 0), (5, 0)),
            ((5, 0), (5, 4)),
            ((5, 4), (0, 4)),
            # Missing closing wall
        ]

        path = create_simple_dxf(walls)
        try:
            parser = DWGParser(auto_detect_rooms=True)
            floor_plan = parser.parse(path)
            assert len(floor_plan.rooms) == 0
        finally:
            os.unlink(path)

    def test_very_small_room_filtered(self):
        """Rooms below minimum area threshold should be filtered."""
        # Create a tiny 0.3x0.3m room (0.09 sq m - below 0.5 threshold)
        walls = [
            ((0, 0), (0.3, 0)),
            ((0.3, 0), (0.3, 0.3)),
            ((0.3, 0.3), (0, 0.3)),
            ((0, 0.3), (0, 0)),
        ]

        path = create_simple_dxf(walls)
        try:
            parser = DWGParser(auto_detect_rooms=True)
            floor_plan = parser.parse(path)
            # Tiny room should be filtered
            assert len(floor_plan.rooms) == 0
        finally:
            os.unlink(path)

    def test_complex_floor_plan_multiple_rooms(self):
        """Complex floor plan with multiple rooms of different shapes."""
        # Create a more complex layout with properly connected walls:
        #
        # +----+----+----+
        # | R1 | R2 | R3 |   (top row: 3 rooms)
        # +----+----+----+
        # |   R4   |  R5 |   (bottom row: 2 rooms)
        # +--------+-----+
        #
        # Walls must share endpoints for WallGraph cycle detection.

        walls = [
            # Bottom boundary split at x=6
            ((0, 0), (6, 0)),
            ((6, 0), (12, 0)),
            # Right boundary split at y=5
            ((12, 0), (12, 5)),
            ((12, 5), (12, 10)),
            # Top boundary split at x=4 and x=8
            ((12, 10), (8, 10)),
            ((8, 10), (4, 10)),
            ((4, 10), (0, 10)),
            # Left boundary split at y=5
            ((0, 10), (0, 5)),
            ((0, 5), (0, 0)),
            # Horizontal corridor at y=5 split at x=4, x=6, x=8
            ((0, 5), (4, 5)),
            ((4, 5), (6, 5)),
            ((6, 5), (8, 5)),
            ((8, 5), (12, 5)),
            # Vertical walls in top row at x=4 and x=8
            ((4, 5), (4, 10)),
            ((8, 5), (8, 10)),
            # Vertical wall in bottom row at x=6
            ((6, 0), (6, 5)),
        ]

        path = create_simple_dxf(walls)
        try:
            parser = DWGParser(auto_detect_rooms=True)
            floor_plan = parser.parse(path)
            # Should detect 5 rooms: 3 top, 2 bottom
            assert len(floor_plan.rooms) == 5
        finally:
            os.unlink(path)
