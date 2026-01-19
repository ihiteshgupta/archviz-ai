# tests/test_shell_builder.py
import pytest
import numpy as np
from core.model_gen.shell_builder import ShellBuilder


class TestShellBuilder:
    """Tests for procedural 3D shell generation from room data."""

    def test_generates_floor_mesh_from_rectangular_room(self):
        """Floor mesh should match room polygon dimensions."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],  # 5m x 4m
        }

        builder = ShellBuilder(room_data)
        floor_mesh = builder.build_floor()

        # Floor should be at y=0, spanning the polygon
        assert floor_mesh is not None
        bounds = floor_mesh.bounds
        assert np.isclose(bounds[0][1], 0)  # min y = 0
        assert np.isclose(bounds[1][1], 0)  # max y = 0 (flat)
        assert np.isclose(bounds[1][0] - bounds[0][0], 5, atol=0.01)  # width ~5m
        assert np.isclose(bounds[1][2] - bounds[0][2], 4, atol=0.01)  # depth ~4m

    def test_generates_ceiling_at_wall_height(self):
        """Ceiling mesh should be at wall_height, matching floor dimensions."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
        }

        builder = ShellBuilder(room_data, wall_height=2.7)
        ceiling_mesh = builder.build_ceiling()

        bounds = ceiling_mesh.bounds
        assert np.isclose(bounds[0][1], 2.7, atol=0.01)  # min y = 2.7
        assert np.isclose(bounds[1][1], 2.7, atol=0.01)  # max y = 2.7

    def test_generates_walls_from_polygon_edges(self):
        """Walls should be generated for each edge of the polygon."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],  # 4 edges
        }

        builder = ShellBuilder(room_data, wall_height=2.7)
        walls = builder.build_walls()

        assert len(walls) == 4  # One wall per edge

        # Each wall should span from y=0 to y=2.7
        for wall in walls:
            bounds = wall.bounds
            assert np.isclose(bounds[0][1], 0, atol=0.01)  # min y = 0
            assert np.isclose(bounds[1][1], 2.7, atol=0.01)  # max y = 2.7
