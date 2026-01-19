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
        self.doors = room_data.get("doors", [])
        self.windows = room_data.get("windows", [])

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
        """Generate wall meshes with door/window cutouts."""
        walls = []
        n = len(self.polygon)

        for i in range(n):
            p1 = self.polygon[i]
            p2 = self.polygon[(i + 1) % n]

            # Get openings for this wall
            wall_doors = [d for d in self.doors if d.get("wall_index") == i]
            wall_windows = [w for w in self.windows if w.get("wall_index") == i]

            wall = self._create_wall_with_openings(p1, p2, wall_doors, wall_windows)
            walls.append(wall)

        return walls

    def _create_wall_quad(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        thickness: float = 0.1,
    ) -> trimesh.Trimesh:
        """Create a volumetric wall between two floor points.

        Args:
            p1: Start point of wall (x, z in 2D space)
            p2: End point of wall (x, z in 2D space)
            thickness: Wall thickness in meters (default 0.1m / 10cm)

        Returns:
            A volumetric wall mesh (box) for CSG operations
        """
        # Calculate wall direction and perpendicular
        wall_vec = p2 - p1
        wall_length = np.linalg.norm(wall_vec)
        if wall_length < 1e-6:
            # Degenerate wall, return empty mesh
            return trimesh.Trimesh()

        wall_dir = wall_vec / wall_length
        perp = np.array([-wall_dir[1], wall_dir[0]])

        # Half thickness offset
        half_t = thickness / 2

        # Create 8 corners of the wall box
        # Bottom face (y=0)
        v0 = [p1[0] - perp[0] * half_t, 0, p1[1] - perp[1] * half_t]
        v1 = [p2[0] - perp[0] * half_t, 0, p2[1] - perp[1] * half_t]
        v2 = [p2[0] + perp[0] * half_t, 0, p2[1] + perp[1] * half_t]
        v3 = [p1[0] + perp[0] * half_t, 0, p1[1] + perp[1] * half_t]

        # Top face (y=wall_height)
        v4 = [p1[0] - perp[0] * half_t, self.wall_height, p1[1] - perp[1] * half_t]
        v5 = [p2[0] - perp[0] * half_t, self.wall_height, p2[1] - perp[1] * half_t]
        v6 = [p2[0] + perp[0] * half_t, self.wall_height, p2[1] + perp[1] * half_t]
        v7 = [p1[0] + perp[0] * half_t, self.wall_height, p1[1] + perp[1] * half_t]

        vertices = np.array([v0, v1, v2, v3, v4, v5, v6, v7])

        # Create box faces (2 triangles per face, 6 faces)
        # Face winding order ensures outward-facing normals for proper CSG
        faces = np.array([
            # Bottom face (y=0) - outward normal is -Y
            [0, 1, 2],
            [0, 2, 3],
            # Top face (y=wall_height) - outward normal is +Y
            [4, 6, 5],
            [4, 7, 6],
            # Front face (inner wall) - outward normal is +perp
            [3, 6, 7],
            [3, 2, 6],
            # Back face (outer wall) - outward normal is -perp
            [0, 5, 1],
            [0, 4, 5],
            # Left face (at p1) - outward normal is -wall_dir
            [0, 7, 4],
            [0, 3, 7],
            # Right face (at p2) - outward normal is +wall_dir
            [1, 6, 2],
            [1, 5, 6],
        ])

        return trimesh.Trimesh(vertices=vertices, faces=faces)

    def _create_wall_with_openings(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        doors: list[dict],
        windows: list[dict],
    ) -> trimesh.Trimesh:
        """Create wall with boolean cutouts for doors and windows."""
        # Create solid wall first
        wall = self._create_wall_quad(p1, p2)

        if not doors and not windows:
            return wall

        # Calculate wall direction vector
        wall_vec = p2 - p1
        wall_length = np.linalg.norm(wall_vec)
        wall_dir = wall_vec / wall_length

        # Create cutout boxes and subtract them
        for door in doors:
            cutout = self._create_opening_box(
                p1,
                wall_dir,
                door["position"],
                door["width"],
                0,
                door["height"],  # Doors start at floor
            )
            wall = wall.difference(cutout)

        for window in windows:
            sill = window.get("sill_height", 0.9)
            cutout = self._create_opening_box(
                p1,
                wall_dir,
                window["position"],
                window["width"],
                sill,
                sill + window["height"],
            )
            wall = wall.difference(cutout)

        return wall

    def _create_opening_box(
        self,
        wall_start: np.ndarray,
        wall_dir: np.ndarray,
        position: float,
        width: float,
        bottom: float,
        top: float,
    ) -> trimesh.Trimesh:
        """Create a box for boolean subtraction (door/window opening)."""
        # Calculate opening position along wall
        start_pos = wall_start + wall_dir * position
        end_pos = wall_start + wall_dir * (position + width)

        # Create box extending through wall (0.5m thick to ensure clean cut)
        # Perpendicular direction
        perp = np.array([-wall_dir[1], wall_dir[0]])

        vertices = np.array([
            # Bottom face
            [start_pos[0] - perp[0] * 0.25, bottom, start_pos[1] - perp[1] * 0.25],
            [end_pos[0] - perp[0] * 0.25, bottom, end_pos[1] - perp[1] * 0.25],
            [end_pos[0] + perp[0] * 0.25, bottom, end_pos[1] + perp[1] * 0.25],
            [start_pos[0] + perp[0] * 0.25, bottom, start_pos[1] + perp[1] * 0.25],
            # Top face
            [start_pos[0] - perp[0] * 0.25, top, start_pos[1] - perp[1] * 0.25],
            [end_pos[0] - perp[0] * 0.25, top, end_pos[1] - perp[1] * 0.25],
            [end_pos[0] + perp[0] * 0.25, top, end_pos[1] + perp[1] * 0.25],
            [start_pos[0] + perp[0] * 0.25, top, start_pos[1] + perp[1] * 0.25],
        ])

        return trimesh.convex.convex_hull(vertices)

    def build_shell(self) -> trimesh.Scene:
        """Build complete room shell as a trimesh Scene."""
        scene = trimesh.Scene()

        # Add floor
        floor = self.build_floor()
        scene.add_geometry(floor, node_name="floor", geom_name="floor")

        # Add ceiling
        ceiling = self.build_ceiling()
        scene.add_geometry(ceiling, node_name="ceiling", geom_name="ceiling")

        # Add walls
        walls = self.build_walls()
        for i, wall in enumerate(walls):
            name = f"wall_{i}"
            scene.add_geometry(wall, node_name=name, geom_name=name)

        return scene

    def export_gltf(self, output_path: str) -> None:
        """Export complete shell to glTF/GLB file."""
        scene = self.build_shell()
        scene.export(output_path)
