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

    def test_walls_have_door_cutouts(self):
        """Walls should have boolean cutouts for doors."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "doors": [
                {
                    "wall_index": 0,  # South wall (0,0 to 5,0)
                    "position": 2.0,  # 2m from start of wall
                    "width": 0.9,
                    "height": 2.1,
                }
            ],
        }

        builder = ShellBuilder(room_data, wall_height=2.7)
        walls = builder.build_walls()

        # South wall should have opening (fewer faces than solid wall)
        south_wall = walls[0]
        solid_builder = ShellBuilder({"id": "x", "polygon": room_data["polygon"]})
        solid_walls = solid_builder.build_walls()
        solid_south = solid_walls[0]

        # Wall with door should have more faces due to cutout geometry
        assert len(south_wall.faces) > len(solid_south.faces)

    def test_walls_have_window_cutouts(self):
        """Walls should have boolean cutouts for windows."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "windows": [
                {
                    "wall_index": 1,  # East wall (5,0 to 5,4)
                    "position": 1.0,  # 1m from start of wall
                    "width": 1.2,
                    "height": 1.0,
                    "sill_height": 0.9,  # Window starts at 0.9m
                }
            ],
        }

        builder = ShellBuilder(room_data, wall_height=2.7)
        walls = builder.build_walls()

        # East wall should have opening
        east_wall = walls[1]
        solid_builder = ShellBuilder({"id": "x", "polygon": room_data["polygon"]})
        solid_walls = solid_builder.build_walls()
        solid_east = solid_walls[1]

        # Wall with window should have more faces due to cutout geometry
        assert len(east_wall.faces) > len(solid_east.faces)

    def test_multiple_openings_on_same_wall(self):
        """A wall can have multiple doors and windows."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [8, 0], [8, 4], [0, 4]],  # 8m wide wall
            "doors": [
                {
                    "wall_index": 0,
                    "position": 1.0,
                    "width": 0.9,
                    "height": 2.1,
                }
            ],
            "windows": [
                {
                    "wall_index": 0,
                    "position": 5.0,
                    "width": 1.5,
                    "height": 1.2,
                    "sill_height": 0.9,
                }
            ],
        }

        builder = ShellBuilder(room_data, wall_height=2.7)
        walls = builder.build_walls()

        # South wall should have both openings
        south_wall = walls[0]
        solid_builder = ShellBuilder({"id": "x", "polygon": room_data["polygon"]})
        solid_walls = solid_builder.build_walls()
        solid_south = solid_walls[0]

        # Wall with multiple openings should have even more faces
        assert len(south_wall.faces) > len(solid_south.faces)

    def test_exports_complete_shell_to_gltf(self):
        """Complete shell should export to valid glTF file."""
        import tempfile
        import os

        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "doors": [{"wall_index": 0, "position": 2.0, "width": 0.9, "height": 2.1}],
        }

        builder = ShellBuilder(room_data)

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            output_path = f.name

        try:
            builder.export_gltf(output_path)

            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

            # Verify it's valid glTF by loading it
            import trimesh
            scene = trimesh.load(output_path)

            # Should have floor, ceiling, and walls
            mesh_names = list(scene.geometry.keys())
            assert any("floor" in name.lower() for name in mesh_names)
            assert any("ceiling" in name.lower() for name in mesh_names)
            assert any("wall" in name.lower() for name in mesh_names)
        finally:
            os.unlink(output_path)
