"""DXF Floor Plan Parser

Extracts architectural elements (walls, doors, windows, rooms) from DXF files
using the ezdxf library.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

import ezdxf
from ezdxf.document import Drawing
from ezdxf.entities import DXFEntity, Insert, Line, LWPolyline

from .converter import convert_dwg_to_dxf, is_dwg_file
from .elements import Dimension, Door, Point2D, Room, Wall, Window
from .room_classifier import RoomClassifier, RoomContext
from .spatial_utils import point_in_polygon, polygon_area, polygon_centroid
from .wall_graph import WallGraph

logger = logging.getLogger(__name__)


# Common layer name patterns for architectural elements
WALL_LAYER_PATTERNS = ["wall", "walls", "a-wall", "arch-wall", "mur", "wand"]
DOOR_LAYER_PATTERNS = ["door", "doors", "a-door", "arch-door", "porte", "tuer"]
WINDOW_LAYER_PATTERNS = ["window", "windows", "a-glaz", "arch-window", "fenetre", "fenster"]
ROOM_LAYER_PATTERNS = ["room", "rooms", "space", "area", "a-area", "raum", "piece"]

# Common block name patterns
DOOR_BLOCK_PATTERNS = ["door", "dr", "d-", "porte", "tuer"]
WINDOW_BLOCK_PATTERNS = ["window", "win", "w-", "fenetre", "fenster"]


@dataclass
class FloorPlanMetadata:
    """Metadata about the parsed floor plan."""

    filename: str = ""
    units: str = "meters"
    scale: float = 1.0
    bounds_min: Point2D = (0.0, 0.0)
    bounds_max: Point2D = (0.0, 0.0)
    total_area: float = 0.0
    floor_count: int = 1

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "units": self.units,
            "scale": self.scale,
            "bounds": {
                "min": list(self.bounds_min),
                "max": list(self.bounds_max),
            },
            "total_area": round(self.total_area, 2),
            "floor_count": self.floor_count,
        }


@dataclass
class FloorPlan:
    """Complete floor plan data structure."""

    metadata: FloorPlanMetadata = field(default_factory=FloorPlanMetadata)
    walls: List[Wall] = field(default_factory=list)
    doors: List[Door] = field(default_factory=list)
    windows: List[Window] = field(default_factory=list)
    rooms: List[Room] = field(default_factory=list)
    dimensions: List[Dimension] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "walls": [w.to_dict() for w in self.walls],
            "doors": [d.to_dict() for d in self.doors],
            "windows": [w.to_dict() for w in self.windows],
            "rooms": [r.to_dict() for r in self.rooms],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "summary": {
                "wall_count": len(self.walls),
                "door_count": len(self.doors),
                "window_count": len(self.windows),
                "room_count": len(self.rooms),
                "total_wall_length": round(sum(w.length for w in self.walls), 2),
                "total_room_area": round(sum(r.area for r in self.rooms), 2),
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save_json(self, path: str | Path) -> None:
        """Save floor plan to JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())


class DWGParser:
    """Parser for DWG/DXF architectural floor plans."""

    def __init__(
        self,
        wall_layers: Optional[List[str]] = None,
        door_layers: Optional[List[str]] = None,
        window_layers: Optional[List[str]] = None,
        default_wall_height: float = 3.0,
        default_wall_thickness: float = 0.2,
        snap_tolerance: float = 0.05,
        auto_detect_rooms: bool = True,
        openai_service: Optional[Any] = None,
    ):
        """
        Initialize the parser.

        Args:
            wall_layers: Custom layer names to look for walls
            door_layers: Custom layer names to look for doors
            window_layers: Custom layer names to look for windows
            default_wall_height: Default wall height in meters
            default_wall_thickness: Default wall thickness in meters
            snap_tolerance: Distance within which wall endpoints are merged (meters)
            auto_detect_rooms: Whether to automatically detect rooms from walls
            openai_service: Optional Azure OpenAI service for AI room classification
        """
        self.wall_layers = wall_layers or []
        self.door_layers = door_layers or []
        self.window_layers = window_layers or []
        self.default_wall_height = default_wall_height
        self.default_wall_thickness = default_wall_thickness
        self.snap_tolerance = snap_tolerance
        self.auto_detect_rooms = auto_detect_rooms
        self.openai_service = openai_service

        self._doc: Optional[Drawing] = None
        self._floor_plan: Optional[FloorPlan] = None

    def parse(self, file_path: str | Path) -> FloorPlan:
        """
        Parse a DWG or DXF file and extract floor plan elements.

        Args:
            file_path: Path to DWG or DXF file

        Returns:
            FloorPlan object with extracted elements
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Convert DWG to DXF if needed
        if is_dwg_file(file_path):
            logger.info(f"Converting DWG to DXF: {file_path}")
            dxf_path = convert_dwg_to_dxf(file_path)
            if dxf_path is None:
                raise RuntimeError(f"Failed to convert DWG file: {file_path}")
            file_path = dxf_path

        # Load DXF file
        logger.info(f"Loading DXF file: {file_path}")
        self._doc = ezdxf.readfile(str(file_path))

        # Initialize floor plan
        self._floor_plan = FloorPlan()
        self._floor_plan.metadata.filename = file_path.name

        # Detect units and scale
        self._detect_units()

        # Extract elements
        self._extract_walls()
        self._extract_doors()
        self._extract_windows()

        # Room detection: either from wall geometry or from room layers
        if self.auto_detect_rooms:
            self._detect_rooms_from_walls()
        else:
            self._extract_rooms()

        self._extract_dimensions()

        # Calculate bounds
        self._calculate_bounds()

        return self._floor_plan

    def _detect_units(self) -> None:
        """Detect drawing units from DXF header."""
        if self._doc is None:
            return

        # Check INSUNITS header variable
        try:
            insunits = self._doc.header.get("$INSUNITS", 0)
            unit_map = {
                0: "unitless",
                1: "inches",
                2: "feet",
                3: "miles",
                4: "millimeters",
                5: "centimeters",
                6: "meters",
                7: "kilometers",
            }
            self._floor_plan.metadata.units = unit_map.get(insunits, "meters")

            # Set scale to convert to meters
            scale_map = {
                1: 0.0254,  # inches to meters
                2: 0.3048,  # feet to meters
                4: 0.001,  # mm to meters
                5: 0.01,  # cm to meters
                6: 1.0,  # meters
            }
            self._floor_plan.metadata.scale = scale_map.get(insunits, 1.0)

        except Exception as e:
            logger.warning(f"Could not detect units: {e}")
            self._floor_plan.metadata.units = "meters"
            self._floor_plan.metadata.scale = 1.0

    def _is_wall_layer(self, layer_name: str) -> bool:
        """Check if layer name indicates walls."""
        layer_lower = layer_name.lower()

        # Check custom layers first
        if layer_name in self.wall_layers or layer_lower in [
            layer.lower() for layer in self.wall_layers
        ]:
            return True

        # Check common patterns
        return any(pattern in layer_lower for pattern in WALL_LAYER_PATTERNS)

    def _is_door_layer(self, layer_name: str) -> bool:
        """Check if layer name indicates doors."""
        layer_lower = layer_name.lower()

        if layer_name in self.door_layers or layer_lower in [
            layer.lower() for layer in self.door_layers
        ]:
            return True

        return any(pattern in layer_lower for pattern in DOOR_LAYER_PATTERNS)

    def _is_window_layer(self, layer_name: str) -> bool:
        """Check if layer name indicates windows."""
        layer_lower = layer_name.lower()

        if layer_name in self.window_layers or layer_lower in [
            layer.lower() for layer in self.window_layers
        ]:
            return True

        return any(pattern in layer_lower for pattern in WINDOW_LAYER_PATTERNS)

    def _is_door_block(self, block_name: str) -> bool:
        """Check if block name indicates a door."""
        block_lower = block_name.lower()
        return any(pattern in block_lower for pattern in DOOR_BLOCK_PATTERNS)

    def _is_window_block(self, block_name: str) -> bool:
        """Check if block name indicates a window."""
        block_lower = block_name.lower()
        return any(pattern in block_lower for pattern in WINDOW_BLOCK_PATTERNS)

    def _extract_walls(self) -> None:
        """Extract wall elements from DXF."""
        if self._doc is None or self._floor_plan is None:
            return

        msp = self._doc.modelspace()
        scale = self._floor_plan.metadata.scale

        for entity in msp:
            layer = entity.dxf.layer

            # Check if this is a wall layer
            if not self._is_wall_layer(layer):
                continue

            # Extract wall geometry
            wall = self._entity_to_wall(entity, scale)
            if wall is not None:
                wall.layer = layer
                self._floor_plan.walls.append(wall)

        logger.info(f"Extracted {len(self._floor_plan.walls)} walls")

    def _entity_to_wall(self, entity: DXFEntity, scale: float) -> Optional[Wall]:
        """Convert a DXF entity to a Wall object."""
        points: List[Point2D] = []

        if isinstance(entity, LWPolyline):
            # Lightweight polyline - most common for walls
            for x, y, *_ in entity.get_points():
                points.append((x * scale, y * scale))

        elif isinstance(entity, Line):
            # Simple line
            start = entity.dxf.start
            end = entity.dxf.end
            points = [
                (start.x * scale, start.y * scale),
                (end.x * scale, end.y * scale),
            ]

        else:
            return None

        if len(points) < 2:
            return None

        return Wall(
            points=points,
            thickness=self.default_wall_thickness,
            height=self.default_wall_height,
        )

    def _extract_doors(self) -> None:
        """Extract door elements from DXF."""
        if self._doc is None or self._floor_plan is None:
            return

        msp = self._doc.modelspace()
        scale = self._floor_plan.metadata.scale

        for entity in msp:
            if not isinstance(entity, Insert):
                continue

            block_name = entity.dxf.name
            layer = entity.dxf.layer

            # Check if this is a door
            if not (self._is_door_block(block_name) or self._is_door_layer(layer)):
                continue

            # Extract door info
            insert_point = entity.dxf.insert
            rotation = entity.dxf.rotation if hasattr(entity.dxf, "rotation") else 0

            door = Door(
                position=(insert_point.x * scale, insert_point.y * scale),
                angle=rotation,
                layer=layer,
            )

            # Try to get width from block
            try:
                block = self._doc.blocks.get(block_name)
                if block:
                    bounds = self._get_block_bounds(block)
                    if bounds:
                        door.width = abs(bounds[1][0] - bounds[0][0]) * scale
            except Exception:
                pass

            self._floor_plan.doors.append(door)

        logger.info(f"Extracted {len(self._floor_plan.doors)} doors")

    def _extract_windows(self) -> None:
        """Extract window elements from DXF."""
        if self._doc is None or self._floor_plan is None:
            return

        msp = self._doc.modelspace()
        scale = self._floor_plan.metadata.scale

        for entity in msp:
            if not isinstance(entity, Insert):
                continue

            block_name = entity.dxf.name
            layer = entity.dxf.layer

            # Check if this is a window
            if not (self._is_window_block(block_name) or self._is_window_layer(layer)):
                continue

            # Extract window info
            insert_point = entity.dxf.insert
            rotation = entity.dxf.rotation if hasattr(entity.dxf, "rotation") else 0

            window = Window(
                position=(insert_point.x * scale, insert_point.y * scale),
                angle=rotation,
                layer=layer,
            )

            # Try to get width from block
            try:
                block = self._doc.blocks.get(block_name)
                if block:
                    bounds = self._get_block_bounds(block)
                    if bounds:
                        window.width = abs(bounds[1][0] - bounds[0][0]) * scale
            except Exception:
                pass

            self._floor_plan.windows.append(window)

        logger.info(f"Extracted {len(self._floor_plan.windows)} windows")

    def _extract_rooms(self) -> None:
        """Extract room/space elements from DXF."""
        if self._doc is None or self._floor_plan is None:
            return

        msp = self._doc.modelspace()
        scale = self._floor_plan.metadata.scale

        for entity in msp:
            layer = entity.dxf.layer.lower()

            # Look for closed polylines on room layers
            if not any(pattern in layer for pattern in ROOM_LAYER_PATTERNS):
                continue

            if isinstance(entity, LWPolyline) and entity.closed:
                points: List[Point2D] = []
                for x, y, *_ in entity.get_points():
                    points.append((x * scale, y * scale))

                if len(points) >= 3:
                    room = Room(
                        polygon=points,
                        name=self._extract_room_name(entity),
                    )
                    self._floor_plan.rooms.append(room)

        logger.info(f"Extracted {len(self._floor_plan.rooms)} rooms")

    def _extract_room_name(self, entity: DXFEntity) -> str:
        """Try to extract room name from nearby text entities."""
        # This is a simplified version - in practice, you'd search for
        # text entities near the room centroid
        return ""

    def _extract_dimensions(self) -> None:
        """Extract dimension annotations from DXF."""
        if self._doc is None or self._floor_plan is None:
            return

        msp = self._doc.modelspace()
        scale = self._floor_plan.metadata.scale

        for entity in msp:
            if entity.dxftype() == "DIMENSION":
                try:
                    dim = Dimension(
                        start=(
                            entity.dxf.defpoint.x * scale,
                            entity.dxf.defpoint.y * scale,
                        ),
                        end=(
                            entity.dxf.defpoint2.x * scale,
                            entity.dxf.defpoint2.y * scale,
                        ),
                        value=(
                            entity.dxf.actual_measurement * scale
                            if hasattr(entity.dxf, "actual_measurement")
                            else 0
                        ),
                        text=entity.dxf.text if hasattr(entity.dxf, "text") else "",
                    )
                    self._floor_plan.dimensions.append(dim)
                except Exception as e:
                    logger.debug(f"Could not extract dimension: {e}")

        logger.info(f"Extracted {len(self._floor_plan.dimensions)} dimensions")

    def _get_block_bounds(self, block) -> Optional[Tuple[Point2D, Point2D]]:
        """Get bounding box of a block definition."""
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for entity in block:
            if isinstance(entity, (Line, LWPolyline)):
                if isinstance(entity, Line):
                    points = [
                        (entity.dxf.start.x, entity.dxf.start.y),
                        (entity.dxf.end.x, entity.dxf.end.y),
                    ]
                else:
                    points = [(x, y) for x, y, *_ in entity.get_points()]

                for x, y in points:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if min_x == float("inf"):
            return None

        return ((min_x, min_y), (max_x, max_y))

    def _calculate_bounds(self) -> None:
        """Calculate overall floor plan bounds."""
        if self._floor_plan is None:
            return

        all_points: List[Point2D] = []

        # Collect all points
        for wall in self._floor_plan.walls:
            all_points.extend(wall.points)

        for room in self._floor_plan.rooms:
            all_points.extend(room.polygon)

        for door in self._floor_plan.doors:
            all_points.append(door.position)

        for window in self._floor_plan.windows:
            all_points.append(window.position)

        if not all_points:
            return

        min_x = min(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_x = max(p[0] for p in all_points)
        max_y = max(p[1] for p in all_points)

        self._floor_plan.metadata.bounds_min = (min_x, min_y)
        self._floor_plan.metadata.bounds_max = (max_x, max_y)
        self._floor_plan.metadata.total_area = sum(r.area for r in self._floor_plan.rooms)

    def _detect_rooms_from_walls(self) -> None:
        """Detect rooms by finding enclosed areas in wall geometry."""
        if self._floor_plan is None:
            return

        # Build WallGraph from walls
        graph = WallGraph(snap_tolerance=self.snap_tolerance)
        graph.add_walls(self._floor_plan.walls)

        # Find cycles (enclosed rooms)
        cycles = graph.find_cycles(min_area=0.5)

        if not cycles:
            logger.info("No enclosed rooms detected from walls")
            return

        # Create classifier
        classifier = RoomClassifier(openai_service=self.openai_service)

        # Build Room objects from cycles
        for polygon in cycles:
            # Build context for classification
            context = self._build_room_context(polygon)

            # Classify the room
            classification = classifier.classify(context)

            # Create Room object
            room = Room(
                polygon=polygon,
                room_type=classification.room_type,
                confidence_low=classification.is_low_confidence,
            )

            # Try to find a name from nearby text
            centroid = polygon_centroid(polygon)
            nearby_texts = self._find_text_near_centroid(centroid, radius=2.0)
            if nearby_texts:
                room.name = nearby_texts[0]

            self._floor_plan.rooms.append(room)

        logger.info(f"Detected {len(self._floor_plan.rooms)} rooms from walls")

    def _build_room_context(self, polygon: List[Point2D]) -> RoomContext:
        """Build classification context for a room polygon.

        Args:
            polygon: List of (x, y) vertices defining the room boundary

        Returns:
            RoomContext with area, aspect ratio, door/window counts, fixtures, and text
        """
        area = polygon_area(polygon)
        centroid = polygon_centroid(polygon)

        # Calculate bounding box for aspect ratio
        min_x = min(p[0] for p in polygon)
        max_x = max(p[0] for p in polygon)
        min_y = min(p[1] for p in polygon)
        max_y = max(p[1] for p in polygon)

        width = max_x - min_x
        height = max_y - min_y
        aspect_ratio = width / height if height > 0 else 1.0

        # Count doors inside or on boundary of polygon
        door_count = 0
        if self._floor_plan:
            for door in self._floor_plan.doors:
                if point_in_polygon(door.position, polygon):
                    door_count += 1

        # Count windows inside or on boundary of polygon
        window_count = 0
        if self._floor_plan:
            for window in self._floor_plan.windows:
                if point_in_polygon(window.position, polygon):
                    window_count += 1

        # Detect fixtures inside polygon
        fixtures = self._detect_fixtures_in_polygon(polygon)

        # Find nearby text
        nearby_text = self._find_text_near_centroid(centroid, radius=2.0)

        return RoomContext(
            polygon=polygon,
            area=area,
            aspect_ratio=aspect_ratio,
            door_count=door_count,
            window_count=window_count,
            fixtures=fixtures,
            nearby_text=nearby_text,
        )

    def _detect_fixtures_in_polygon(self, polygon: List[Point2D]) -> List[str]:
        """Detect fixture blocks inside a polygon.

        Args:
            polygon: List of (x, y) vertices defining the room boundary

        Returns:
            List of fixture block names found inside the polygon
        """
        fixtures: List[str] = []

        if self._doc is None or self._floor_plan is None:
            return fixtures

        msp = self._doc.modelspace()
        scale = self._floor_plan.metadata.scale

        for entity in msp:
            if not isinstance(entity, Insert):
                continue

            block_name = entity.dxf.name
            insert_point = entity.dxf.insert
            position = (insert_point.x * scale, insert_point.y * scale)

            # Check if the block is inside the polygon
            if point_in_polygon(position, polygon):
                # Skip doors and windows (already counted)
                if not self._is_door_block(block_name) and not self._is_window_block(block_name):
                    fixtures.append(block_name)

        return fixtures

    def _find_text_near_centroid(self, centroid: Point2D, radius: float = 2.0) -> List[str]:
        """Find text entities near a point.

        Args:
            centroid: (x, y) coordinates of the search center
            radius: Search radius in meters

        Returns:
            List of text content found near the centroid
        """
        texts: List[str] = []

        if self._doc is None or self._floor_plan is None:
            return texts

        msp = self._doc.modelspace()
        scale = self._floor_plan.metadata.scale

        for entity in msp:
            if entity.dxftype() in ("TEXT", "MTEXT"):
                try:
                    # Get text position
                    if entity.dxftype() == "TEXT":
                        insert = entity.dxf.insert
                        text_content = entity.dxf.text
                    else:  # MTEXT
                        insert = entity.dxf.insert
                        text_content = entity.text

                    position = (insert.x * scale, insert.y * scale)

                    # Calculate distance from centroid
                    dx = position[0] - centroid[0]
                    dy = position[1] - centroid[1]
                    distance = (dx**2 + dy**2) ** 0.5

                    if distance <= radius and text_content:
                        texts.append(text_content.strip())

                except Exception as e:
                    logger.debug(f"Could not extract text from entity: {e}")

        return texts
