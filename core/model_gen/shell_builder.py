"""Procedural 3D shell generation from parsed room data."""

import numpy as np
import trimesh
from typing import Any


class ShellBuilder:
    """Builds 3D geometry for room shell (floor, ceiling, walls) from room data."""

    def __init__(self, room_data: dict[str, Any], wall_height: float = 2.7):
        """
        Initialize shell builder with room data.

        Args:
            room_data: Dict with 'polygon' (list of [x,y] points in meters),
                      'walls', 'doors', 'windows'
            wall_height: Height of walls in meters (default 2.7m)
        """
        self.room_data = room_data
        self.wall_height = wall_height
        self.polygon = np.array(room_data["polygon"])

    def build_floor(self) -> trimesh.Trimesh:
        """Generate floor mesh at y=0 from room polygon."""
        # Create 2D polygon vertices, add z=0 (which becomes y after rotation)
        vertices_2d = self.polygon

        # Triangulate the polygon
        from scipy.spatial import Delaunay
        tri = Delaunay(vertices_2d)

        # Create 3D vertices (x, 0, z) - floor at y=0
        vertices_3d = np.zeros((len(vertices_2d), 3))
        vertices_3d[:, 0] = vertices_2d[:, 0]  # x
        vertices_3d[:, 1] = 0  # y = 0 (floor level)
        vertices_3d[:, 2] = vertices_2d[:, 1]  # z (from 2D y)

        # Create mesh
        mesh = trimesh.Trimesh(vertices=vertices_3d, faces=tri.simplices)
        return mesh

    def build_ceiling(self) -> trimesh.Trimesh:
        """Generate ceiling mesh at wall_height from room polygon."""
        from scipy.spatial import Delaunay

        vertices_2d = self.polygon
        tri = Delaunay(vertices_2d)

        vertices_3d = np.zeros((len(vertices_2d), 3))
        vertices_3d[:, 0] = vertices_2d[:, 0]
        vertices_3d[:, 1] = self.wall_height  # ceiling at wall height
        vertices_3d[:, 2] = vertices_2d[:, 1]

        # Reverse face winding for ceiling to face downward
        faces = tri.simplices[:, ::-1]

        mesh = trimesh.Trimesh(vertices=vertices_3d, faces=faces)
        return mesh

    def build_walls(self) -> list[trimesh.Trimesh]:
        """Generate wall meshes for each polygon edge."""
        walls = []
        n = len(self.polygon)

        for i in range(n):
            p1 = self.polygon[i]
            p2 = self.polygon[(i + 1) % n]

            wall = self._create_wall_quad(p1, p2)
            walls.append(wall)

        return walls

    def _create_wall_quad(
        self,
        p1: np.ndarray,
        p2: np.ndarray
    ) -> trimesh.Trimesh:
        """Create a wall quad between two floor points."""
        # Four corners of the wall
        vertices = np.array([
            [p1[0], 0, p1[1]],              # bottom-left
            [p2[0], 0, p2[1]],              # bottom-right
            [p2[0], self.wall_height, p2[1]],  # top-right
            [p1[0], self.wall_height, p1[1]],  # top-left
        ])

        # Two triangles forming the quad (facing inward)
        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
        ])

        return trimesh.Trimesh(vertices=vertices, faces=faces)
