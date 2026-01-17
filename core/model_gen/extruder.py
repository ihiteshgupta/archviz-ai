"""Wall and room extrusion logic for 3D model generation."""

import math
from typing import List, Optional, Tuple

import numpy as np
import trimesh
from scipy.spatial import Delaunay

from core.dwg_parser.elements import Room, Wall

from .types import Mesh3D

Point2D = Tuple[float, float]


class WallExtruder:
    """Extrudes 2D wall polylines into 3D meshes."""

    def __init__(self, default_height: float = 3.0, default_thickness: float = 0.2):
        self.default_height = default_height
        self.default_thickness = default_thickness

    def extrude_wall(self, wall: Wall) -> Optional[Mesh3D]:
        """Extrude a wall from 2D points to 3D mesh."""
        if len(wall.points) < 2:
            return None

        height = wall.height or self.default_height
        thickness = wall.thickness or self.default_thickness

        # For simple two-point walls, create a box
        if len(wall.points) == 2:
            return self._extrude_simple_wall(wall, height, thickness)

        # For multi-point walls, extrude each segment
        return self._extrude_polyline_wall(wall, height, thickness)

    def _extrude_simple_wall(
        self, wall: Wall, height: float, thickness: float
    ) -> Optional[Mesh3D]:
        """Extrude a simple two-point wall segment."""
        p1, p2 = wall.points[0], wall.points[1]

        # Calculate direction and perpendicular
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx * dx + dy * dy)

        if length < 1e-6:
            return None

        # Normalized perpendicular vector
        nx = -dy / length
        ny = dx / length

        # Half thickness offset
        half_t = thickness / 2

        # Create 8 vertices (4 bottom, 4 top)
        vertices = np.array(
            [
                # Bottom face
                [p1[0] - nx * half_t, p1[1] - ny * half_t, 0],  # 0: start outer
                [p1[0] + nx * half_t, p1[1] + ny * half_t, 0],  # 1: start inner
                [p2[0] + nx * half_t, p2[1] + ny * half_t, 0],  # 2: end inner
                [p2[0] - nx * half_t, p2[1] - ny * half_t, 0],  # 3: end outer
                # Top face
                [p1[0] - nx * half_t, p1[1] - ny * half_t, height],  # 4: start outer
                [p1[0] + nx * half_t, p1[1] + ny * half_t, height],  # 5: start inner
                [p2[0] + nx * half_t, p2[1] + ny * half_t, height],  # 6: end inner
                [p2[0] - nx * half_t, p2[1] - ny * half_t, height],  # 7: end outer
            ]
        )

        # Create faces (triangles)
        faces = np.array(
            [
                # Bottom face
                [0, 2, 1],
                [0, 3, 2],
                # Top face
                [4, 5, 6],
                [4, 6, 7],
                # Front face (outer)
                [0, 4, 7],
                [0, 7, 3],
                # Back face (inner)
                [1, 2, 6],
                [1, 6, 5],
                # Start cap
                [0, 1, 5],
                [0, 5, 4],
                # End cap
                [3, 7, 6],
                [3, 6, 2],
            ]
        )

        material_id = "wall_exterior" if wall.is_exterior else "wall_interior"

        return Mesh3D(
            vertices=vertices,
            faces=faces,
            material_id=material_id,
            element_type="walls",
            source_id=wall.id,
        )

    def _extrude_polyline_wall(
        self, wall: Wall, height: float, thickness: float
    ) -> Optional[Mesh3D]:
        """Extrude a multi-point wall with miter joints at corners."""
        points = wall.points
        n = len(points)
        half_t = thickness / 2

        # Calculate offset points for inner and outer edges
        outer_points = []
        inner_points = []

        for i in range(n):
            # Get adjacent segments
            prev_idx = (i - 1) % n if i > 0 else None
            next_idx = i + 1 if i < n - 1 else None

            # Calculate directions
            if prev_idx is not None:
                d1 = self._normalize(
                    (
                        points[i][0] - points[prev_idx][0],
                        points[i][1] - points[prev_idx][1],
                    )
                )
            else:
                d1 = None

            if next_idx is not None:
                d2 = self._normalize(
                    (
                        points[next_idx][0] - points[i][0],
                        points[next_idx][1] - points[i][1],
                    )
                )
            else:
                d2 = None

            # Calculate perpendicular (miter direction)
            if d1 is None:
                perp = (-d2[1], d2[0])
            elif d2 is None:
                perp = (-d1[1], d1[0])
            else:
                # Average the perpendiculars for miter joint
                p1 = (-d1[1], d1[0])
                p2 = (-d2[1], d2[0])
                avg = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
                perp = self._normalize(avg) if self._length(avg) > 1e-6 else p1

                # Clamp miter length to prevent spikes
                dot = d1[0] * d2[0] + d1[1] * d2[1]
                if dot < -0.5:  # Acute angle < ~60 degrees
                    # Use bevel instead
                    perp = p2

            outer_points.append(
                (points[i][0] - perp[0] * half_t, points[i][1] - perp[1] * half_t)
            )
            inner_points.append(
                (points[i][0] + perp[0] * half_t, points[i][1] + perp[1] * half_t)
            )

        # Build vertices: outer bottom, inner bottom, outer top, inner top
        vertices = []
        for p in outer_points:
            vertices.append([p[0], p[1], 0])
        for p in inner_points:
            vertices.append([p[0], p[1], 0])
        for p in outer_points:
            vertices.append([p[0], p[1], height])
        for p in inner_points:
            vertices.append([p[0], p[1], height])

        vertices = np.array(vertices)

        # Build faces
        faces = []

        # Outer wall face
        for i in range(n - 1):
            o1, o2 = i, i + 1
            o1_top, o2_top = o1 + 2 * n, o2 + 2 * n
            faces.append([o1, o2, o2_top])
            faces.append([o1, o2_top, o1_top])

        # Inner wall face
        for i in range(n - 1):
            i1, i2 = n + i, n + i + 1
            i1_top, i2_top = i1 + 2 * n, i2 + 2 * n
            faces.append([i1, i1_top, i2_top])
            faces.append([i1, i2_top, i2])

        # Top face
        for i in range(n - 1):
            o1_top = 2 * n + i
            o2_top = 2 * n + i + 1
            i1_top = 3 * n + i
            i2_top = 3 * n + i + 1
            faces.append([o1_top, o2_top, i2_top])
            faces.append([o1_top, i2_top, i1_top])

        # Bottom face
        for i in range(n - 1):
            o1, o2 = i, i + 1
            i1, i2 = n + i, n + i + 1
            faces.append([o1, i2, o2])
            faces.append([o1, i1, i2])

        # Start cap
        faces.append([0, n, 3 * n])
        faces.append([0, 3 * n, 2 * n])

        # End cap
        faces.append([n - 1, 2 * n + n - 1, 3 * n + n - 1])
        faces.append([n - 1, 3 * n + n - 1, 2 * n - 1])

        faces = np.array(faces)

        material_id = "wall_exterior" if wall.is_exterior else "wall_interior"

        return Mesh3D(
            vertices=vertices,
            faces=faces,
            material_id=material_id,
            element_type="walls",
            source_id=wall.id,
        )

    def _normalize(self, v: Tuple[float, float]) -> Tuple[float, float]:
        """Normalize a 2D vector."""
        length = math.sqrt(v[0] * v[0] + v[1] * v[1])
        if length < 1e-6:
            return (0.0, 0.0)
        return (v[0] / length, v[1] / length)

    def _length(self, v: Tuple[float, float]) -> float:
        """Get length of a 2D vector."""
        return math.sqrt(v[0] * v[0] + v[1] * v[1])


class FloorCeilingExtruder:
    """Extrudes room polygons into floor slabs and ceilings."""

    def __init__(self, floor_thickness: float = 0.15, ceiling_thickness: float = 0.05):
        self.floor_thickness = floor_thickness
        self.ceiling_thickness = ceiling_thickness

    def extrude_floor(self, room: Room, z_offset: float = 0.0) -> Optional[Mesh3D]:
        """Create a floor slab from room polygon."""
        if len(room.polygon) < 3:
            return None

        return self._extrude_slab(
            polygon=room.polygon,
            z_bottom=z_offset - self.floor_thickness,
            z_top=z_offset,
            material_id="floor_default",
            element_type="floors",
            source_id=room.id,
        )

    def extrude_ceiling(self, room: Room, z_offset: float = 0.0) -> Optional[Mesh3D]:
        """Create a ceiling from room polygon."""
        if len(room.polygon) < 3:
            return None

        ceiling_z = z_offset + room.ceiling_height

        return self._extrude_slab(
            polygon=room.polygon,
            z_bottom=ceiling_z,
            z_top=ceiling_z + self.ceiling_thickness,
            material_id="ceiling_default",
            element_type="ceilings",
            source_id=room.id,
        )

    def _extrude_slab(
        self,
        polygon: List[Point2D],
        z_bottom: float,
        z_top: float,
        material_id: str,
        element_type: str,
        source_id: str,
    ) -> Optional[Mesh3D]:
        """Extrude a 2D polygon into a 3D slab."""
        n = len(polygon)
        if n < 3:
            return None

        # Convert polygon to numpy array
        poly_2d = np.array(polygon)

        # Triangulate the polygon
        try:
            tri = Delaunay(poly_2d)
            tri_faces = tri.simplices
        except Exception:
            # Fall back to simple fan triangulation for convex polygons
            tri_faces = np.array([[0, i, i + 1] for i in range(1, n - 1)])

        # Create vertices: bottom + top
        vertices_bottom = np.column_stack([poly_2d, np.full(n, z_bottom)])
        vertices_top = np.column_stack([poly_2d, np.full(n, z_top)])
        vertices = np.vstack([vertices_bottom, vertices_top])

        # Create faces
        faces = []

        # Bottom face (flip winding for correct normals)
        for f in tri_faces:
            faces.append([f[0], f[2], f[1]])

        # Top face
        for f in tri_faces:
            faces.append([f[0] + n, f[1] + n, f[2] + n])

        # Side faces
        for i in range(n):
            i_next = (i + 1) % n
            # Bottom to top
            faces.append([i, i_next, i_next + n])
            faces.append([i, i_next + n, i + n])

        faces = np.array(faces)

        return Mesh3D(
            vertices=vertices,
            faces=faces,
            material_id=material_id,
            element_type=element_type,
            source_id=source_id,
        )
