"""Door and window geometry generation with boolean cutouts."""

import math
from typing import List, Optional, Tuple

import numpy as np
import trimesh

from core.dwg_parser.elements import Door, DoorSwing, Wall, Window, WindowType

from .types import Mesh3D

Point2D = Tuple[float, float]


class OpeningProcessor:
    """Creates door/window geometry and cuts holes in walls."""

    def __init__(
        self,
        frame_width: float = 0.05,
        frame_depth: float = 0.05,
        door_thickness: float = 0.04,
        glass_thickness: float = 0.006,
    ):
        self.frame_width = frame_width
        self.frame_depth = frame_depth
        self.door_thickness = door_thickness
        self.glass_thickness = glass_thickness

    def create_cutting_box(
        self,
        position: Point2D,
        width: float,
        height: float,
        angle: float,
        wall_thickness: float,
        bottom_offset: float = 0.0,
    ) -> trimesh.Trimesh:
        """Create a box for boolean cutting of wall openings."""
        # Add tolerance for clean cuts
        tolerance = 0.002
        extended_width = width + tolerance
        extended_depth = wall_thickness + 0.02  # Extend through wall

        # Create box centered at origin
        box = trimesh.creation.box(
            extents=[extended_width, extended_depth, height + tolerance]
        )

        # Move box so bottom is at bottom_offset
        box.apply_translation([0, 0, height / 2 + bottom_offset])

        # Rotate by angle
        rotation = trimesh.transformations.rotation_matrix(
            math.radians(angle), [0, 0, 1]
        )
        box.apply_transform(rotation)

        # Translate to position
        box.apply_translation([position[0], position[1], 0])

        return box

    def cut_opening_in_wall(
        self, wall_mesh: Mesh3D, cutting_box: trimesh.Trimesh
    ) -> Optional[Mesh3D]:
        """Cut an opening in a wall mesh using boolean difference."""
        wall_trimesh = wall_mesh.to_trimesh()

        if wall_trimesh.vertices.shape[0] == 0:
            return wall_mesh

        try:
            result = wall_trimesh.difference(cutting_box, engine="blender")
            if result is None or result.vertices.shape[0] == 0:
                # Boolean failed, return original
                return wall_mesh

            return Mesh3D.from_trimesh(
                result,
                material_id=wall_mesh.material_id,
                element_type=wall_mesh.element_type,
                source_id=wall_mesh.source_id,
            )
        except Exception:
            # Boolean operation failed, try manifold engine or return original
            try:
                result = wall_trimesh.difference(cutting_box, engine="manifold")
                if result is not None and result.vertices.shape[0] > 0:
                    return Mesh3D.from_trimesh(
                        result,
                        material_id=wall_mesh.material_id,
                        element_type=wall_mesh.element_type,
                        source_id=wall_mesh.source_id,
                    )
            except Exception:
                pass
            return wall_mesh

    def create_door_geometry(
        self, door: Door, wall_thickness: float = 0.2
    ) -> List[Mesh3D]:
        """Create door frame and panel geometry."""
        meshes = []

        width = door.width
        height = door.height
        angle = door.angle
        pos = door.position

        # Frame dimensions
        fw = self.frame_width
        fd = min(self.frame_depth, wall_thickness)

        # Left jamb
        left_jamb = self._create_box(
            width=fw,
            depth=fd,
            height=height,
            position=(pos[0] - width / 2 + fw / 2, pos[1]),
            z_offset=0,
            angle=angle,
        )
        meshes.append(
            Mesh3D.from_trimesh(
                left_jamb,
                material_id="door_frame",
                element_type="door_frames",
                source_id=door.id,
            )
        )

        # Right jamb
        right_jamb = self._create_box(
            width=fw,
            depth=fd,
            height=height,
            position=(pos[0] + width / 2 - fw / 2, pos[1]),
            z_offset=0,
            angle=angle,
        )
        meshes.append(
            Mesh3D.from_trimesh(
                right_jamb,
                material_id="door_frame",
                element_type="door_frames",
                source_id=door.id,
            )
        )

        # Header
        header = self._create_box(
            width=width,
            depth=fd,
            height=fw,
            position=pos,
            z_offset=height - fw,
            angle=angle,
        )
        meshes.append(
            Mesh3D.from_trimesh(
                header,
                material_id="door_frame",
                element_type="door_frames",
                source_id=door.id,
            )
        )

        # Door panel
        panel_width = width - 2 * fw - 0.01  # Small gap
        panel_height = height - fw - 0.01
        panel = self._create_box(
            width=panel_width,
            depth=self.door_thickness,
            height=panel_height,
            position=pos,
            z_offset=0.005,  # Slight lift from floor
            angle=angle,
        )
        meshes.append(
            Mesh3D.from_trimesh(
                panel,
                material_id="door_panel",
                element_type="door_panels",
                source_id=door.id,
            )
        )

        return meshes

    def create_window_geometry(
        self, window: Window, wall_thickness: float = 0.2
    ) -> List[Mesh3D]:
        """Create window frame and glass geometry."""
        meshes = []

        width = window.width
        height = window.height
        sill_height = window.sill_height
        angle = window.angle
        pos = window.position

        # Frame dimensions
        fw = self.frame_width
        fd = min(self.frame_depth, wall_thickness)

        # Left frame
        left_frame = self._create_box(
            width=fw,
            depth=fd,
            height=height,
            position=(pos[0] - width / 2 + fw / 2, pos[1]),
            z_offset=sill_height,
            angle=angle,
        )
        meshes.append(
            Mesh3D.from_trimesh(
                left_frame,
                material_id="window_frame",
                element_type="window_frames",
                source_id=window.id,
            )
        )

        # Right frame
        right_frame = self._create_box(
            width=fw,
            depth=fd,
            height=height,
            position=(pos[0] + width / 2 - fw / 2, pos[1]),
            z_offset=sill_height,
            angle=angle,
        )
        meshes.append(
            Mesh3D.from_trimesh(
                right_frame,
                material_id="window_frame",
                element_type="window_frames",
                source_id=window.id,
            )
        )

        # Top frame
        top_frame = self._create_box(
            width=width,
            depth=fd,
            height=fw,
            position=pos,
            z_offset=sill_height + height - fw,
            angle=angle,
        )
        meshes.append(
            Mesh3D.from_trimesh(
                top_frame,
                material_id="window_frame",
                element_type="window_frames",
                source_id=window.id,
            )
        )

        # Bottom frame (sill)
        sill = self._create_box(
            width=width,
            depth=fd,
            height=fw,
            position=pos,
            z_offset=sill_height,
            angle=angle,
        )
        meshes.append(
            Mesh3D.from_trimesh(
                sill,
                material_id="window_frame",
                element_type="window_frames",
                source_id=window.id,
            )
        )

        # Glass pane
        glass_width = width - 2 * fw - 0.01
        glass_height = height - 2 * fw - 0.01
        glass = self._create_box(
            width=glass_width,
            depth=self.glass_thickness,
            height=glass_height,
            position=pos,
            z_offset=sill_height + fw + 0.005,
            angle=angle,
        )
        meshes.append(
            Mesh3D.from_trimesh(
                glass,
                material_id="glass",
                element_type="window_glass",
                source_id=window.id,
            )
        )

        return meshes

    def find_parent_wall(
        self, position: Point2D, walls: List[Wall], threshold: float = 0.5
    ) -> Optional[Wall]:
        """Find the wall closest to a given position."""
        best_wall = None
        best_distance = float("inf")

        for wall in walls:
            if len(wall.points) < 2:
                continue

            for i in range(len(wall.points) - 1):
                p1 = wall.points[i]
                p2 = wall.points[i + 1]

                # Project position onto line segment
                dist = self._point_to_segment_distance(position, p1, p2)

                if dist < best_distance and dist < threshold:
                    best_distance = dist
                    best_wall = wall

        return best_wall

    def _point_to_segment_distance(
        self, point: Point2D, seg_start: Point2D, seg_end: Point2D
    ) -> float:
        """Calculate distance from point to line segment."""
        px, py = point
        x1, y1 = seg_start
        x2, y2 = seg_end

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)

    def _create_box(
        self,
        width: float,
        depth: float,
        height: float,
        position: Point2D,
        z_offset: float,
        angle: float,
    ) -> trimesh.Trimesh:
        """Create a box mesh at given position and angle."""
        box = trimesh.creation.box(extents=[width, depth, height])

        # Center Z at z_offset + height/2
        box.apply_translation([0, 0, z_offset + height / 2])

        # Rotate by angle
        if angle != 0:
            rotation = trimesh.transformations.rotation_matrix(
                math.radians(angle), [0, 0, 1]
            )
            box.apply_transform(rotation)

        # Translate to position
        box.apply_translation([position[0], position[1], 0])

        return box
