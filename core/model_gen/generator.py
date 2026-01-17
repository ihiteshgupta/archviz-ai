"""Main 3D model generator that orchestrates the pipeline."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from core.dwg_parser.elements import Door, Room, Wall, Window
from core.dwg_parser.parser import FloorPlan

from .exporter import SceneExporter, export_scene
from .extruder import FloorCeilingExtruder, WallExtruder
from .openings import OpeningProcessor
from .types import Mesh3D, Scene3D


@dataclass
class GeneratorConfig:
    """Configuration options for the model generator."""

    # Wall settings
    default_wall_height: float = 3.0
    default_wall_thickness: float = 0.2

    # Floor/ceiling settings
    floor_thickness: float = 0.15
    ceiling_thickness: float = 0.05
    floor_height: float = 3.0  # Height between floors

    # Opening settings
    frame_width: float = 0.05
    door_thickness: float = 0.04
    glass_thickness: float = 0.006

    # Generation options
    generate_floors: bool = True
    generate_ceilings: bool = True
    generate_door_geometry: bool = True
    generate_window_geometry: bool = True
    cut_openings: bool = True  # Boolean cut doors/windows from walls
    multi_floor: bool = True  # Stack floors if floor_level data exists


class ModelGenerator:
    """
    Generates 3D models from parsed floor plans.

    Pipeline:
    1. Extrude walls from 2D polylines to 3D meshes
    2. Cut door/window openings in walls (boolean difference)
    3. Generate door and window frame/panel geometry
    4. Extrude floor slabs and ceilings from room polygons
    5. Assemble into Scene3D with organized mesh groups
    """

    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()

        # Initialize sub-processors
        self.wall_extruder = WallExtruder(
            default_height=self.config.default_wall_height,
            default_thickness=self.config.default_wall_thickness,
        )
        self.floor_ceiling_extruder = FloorCeilingExtruder(
            floor_thickness=self.config.floor_thickness,
            ceiling_thickness=self.config.ceiling_thickness,
        )
        self.opening_processor = OpeningProcessor(
            frame_width=self.config.frame_width,
            door_thickness=self.config.door_thickness,
            glass_thickness=self.config.glass_thickness,
        )

    def generate(self, floor_plan: FloorPlan) -> Scene3D:
        """
        Generate a complete 3D scene from a floor plan.

        Args:
            floor_plan: Parsed FloorPlan with walls, doors, windows, rooms

        Returns:
            Scene3D with all generated meshes organized by type
        """
        scene = Scene3D()
        scene.metadata = {
            "source": floor_plan.metadata.filename,
            "units": floor_plan.metadata.units,
            "scale": floor_plan.metadata.scale,
        }

        # Determine floor levels
        floor_levels = self._get_floor_levels(floor_plan)
        scene.floor_count = len(floor_levels)

        # Process each floor level
        for level in floor_levels:
            z_offset = level * self.config.floor_height if self.config.multi_floor else 0

            # 1. Extrude walls
            wall_meshes = self._extrude_walls(floor_plan.walls, z_offset)

            # 2. Cut openings and generate door/window geometry
            if self.config.cut_openings:
                wall_meshes = self._cut_openings(
                    wall_meshes, floor_plan.doors, floor_plan.windows, floor_plan.walls
                )

            # Add wall meshes to scene
            for mesh in wall_meshes:
                scene.add_mesh(mesh)

            # 3. Generate door geometry
            if self.config.generate_door_geometry:
                door_meshes = self._generate_door_geometry(
                    floor_plan.doors, floor_plan.walls, z_offset
                )
                for mesh in door_meshes:
                    scene.add_mesh(mesh)

            # 4. Generate window geometry
            if self.config.generate_window_geometry:
                window_meshes = self._generate_window_geometry(
                    floor_plan.windows, floor_plan.walls, z_offset
                )
                for mesh in window_meshes:
                    scene.add_mesh(mesh)

            # 5. Generate floors and ceilings
            floor_rooms = [r for r in floor_plan.rooms if r.floor_level == level]
            if not floor_rooms:
                floor_rooms = floor_plan.rooms  # Use all rooms if no level info

            if self.config.generate_floors:
                floor_meshes = self._extrude_floors(floor_rooms, z_offset)
                for mesh in floor_meshes:
                    scene.add_mesh(mesh)

            if self.config.generate_ceilings:
                ceiling_meshes = self._extrude_ceilings(floor_rooms, z_offset)
                for mesh in ceiling_meshes:
                    scene.add_mesh(mesh)

        return scene

    def _get_floor_levels(self, floor_plan: FloorPlan) -> List[int]:
        """Determine unique floor levels from room data."""
        if not self.config.multi_floor:
            return [0]

        levels = set()
        for room in floor_plan.rooms:
            levels.add(room.floor_level)

        if not levels:
            return [0]

        return sorted(levels)

    def _extrude_walls(self, walls: List[Wall], z_offset: float) -> List[Mesh3D]:
        """Extrude all walls to 3D meshes."""
        meshes = []
        for wall in walls:
            mesh = self.wall_extruder.extrude_wall(wall)
            if mesh:
                # Apply z_offset
                if z_offset != 0:
                    mesh.vertices[:, 2] += z_offset
                meshes.append(mesh)
        return meshes

    def _cut_openings(
        self,
        wall_meshes: List[Mesh3D],
        doors: List[Door],
        windows: List[Window],
        walls: List[Wall],
    ) -> List[Mesh3D]:
        """Cut door and window openings in wall meshes."""
        # Build wall_id to mesh mapping
        wall_mesh_map: Dict[str, Mesh3D] = {}
        for mesh in wall_meshes:
            if mesh.source_id:
                wall_mesh_map[mesh.source_id] = mesh

        # Build wall_id to Wall mapping
        wall_map: Dict[str, Wall] = {w.id: w for w in walls}

        # Cut door openings
        for door in doors:
            wall_id = door.wall_id
            if not wall_id:
                # Try to find parent wall
                parent_wall = self.opening_processor.find_parent_wall(
                    door.position, walls
                )
                if parent_wall:
                    wall_id = parent_wall.id

            if wall_id and wall_id in wall_mesh_map:
                wall = wall_map.get(wall_id)
                wall_thickness = wall.thickness if wall else self.config.default_wall_thickness

                cutting_box = self.opening_processor.create_cutting_box(
                    position=door.position,
                    width=door.width,
                    height=door.height,
                    angle=door.angle,
                    wall_thickness=wall_thickness,
                    bottom_offset=0,
                )

                wall_mesh_map[wall_id] = self.opening_processor.cut_opening_in_wall(
                    wall_mesh_map[wall_id], cutting_box
                )

        # Cut window openings
        for window in windows:
            wall_id = window.wall_id
            if not wall_id:
                parent_wall = self.opening_processor.find_parent_wall(
                    window.position, walls
                )
                if parent_wall:
                    wall_id = parent_wall.id

            if wall_id and wall_id in wall_mesh_map:
                wall = wall_map.get(wall_id)
                wall_thickness = wall.thickness if wall else self.config.default_wall_thickness

                cutting_box = self.opening_processor.create_cutting_box(
                    position=window.position,
                    width=window.width,
                    height=window.height,
                    angle=window.angle,
                    wall_thickness=wall_thickness,
                    bottom_offset=window.sill_height,
                )

                wall_mesh_map[wall_id] = self.opening_processor.cut_opening_in_wall(
                    wall_mesh_map[wall_id], cutting_box
                )

        return list(wall_mesh_map.values())

    def _generate_door_geometry(
        self, doors: List[Door], walls: List[Wall], z_offset: float
    ) -> List[Mesh3D]:
        """Generate door frames and panels."""
        meshes = []
        wall_map: Dict[str, Wall] = {w.id: w for w in walls}

        for door in doors:
            wall = wall_map.get(door.wall_id) if door.wall_id else None
            if not wall:
                wall = self.opening_processor.find_parent_wall(door.position, walls)

            wall_thickness = wall.thickness if wall else self.config.default_wall_thickness

            door_meshes = self.opening_processor.create_door_geometry(
                door, wall_thickness
            )

            for mesh in door_meshes:
                if z_offset != 0:
                    mesh.vertices[:, 2] += z_offset
                meshes.append(mesh)

        return meshes

    def _generate_window_geometry(
        self, windows: List[Window], walls: List[Wall], z_offset: float
    ) -> List[Mesh3D]:
        """Generate window frames and glass."""
        meshes = []
        wall_map: Dict[str, Wall] = {w.id: w for w in walls}

        for window in windows:
            wall = wall_map.get(window.wall_id) if window.wall_id else None
            if not wall:
                wall = self.opening_processor.find_parent_wall(window.position, walls)

            wall_thickness = wall.thickness if wall else self.config.default_wall_thickness

            window_meshes = self.opening_processor.create_window_geometry(
                window, wall_thickness
            )

            for mesh in window_meshes:
                if z_offset != 0:
                    mesh.vertices[:, 2] += z_offset
                meshes.append(mesh)

        return meshes

    def _extrude_floors(self, rooms: List[Room], z_offset: float) -> List[Mesh3D]:
        """Generate floor slabs for all rooms."""
        meshes = []
        for room in rooms:
            mesh = self.floor_ceiling_extruder.extrude_floor(room, z_offset)
            if mesh:
                meshes.append(mesh)
        return meshes

    def _extrude_ceilings(self, rooms: List[Room], z_offset: float) -> List[Mesh3D]:
        """Generate ceilings for all rooms."""
        meshes = []
        for room in rooms:
            mesh = self.floor_ceiling_extruder.extrude_ceiling(room, z_offset)
            if mesh:
                meshes.append(mesh)
        return meshes
