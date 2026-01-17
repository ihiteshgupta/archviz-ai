"""Architectural element data classes for floor plan parsing."""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum
import uuid


Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]


class DoorSwing(Enum):
    """Door swing direction."""
    LEFT = "left"
    RIGHT = "right"
    DOUBLE = "double"
    SLIDING = "sliding"


class WindowType(Enum):
    """Window type classification."""
    SINGLE = "single"
    DOUBLE = "double"
    SLIDING = "sliding"
    FIXED = "fixed"
    BAY = "bay"


@dataclass
class Wall:
    """Represents a wall element in a floor plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    points: List[Point2D] = field(default_factory=list)
    thickness: float = 0.2  # meters
    height: float = 3.0  # meters
    layer: str = ""
    is_exterior: bool = False

    @property
    def length(self) -> float:
        """Calculate total wall length."""
        if len(self.points) < 2:
            return 0.0
        total = 0.0
        for i in range(len(self.points) - 1):
            dx = self.points[i + 1][0] - self.points[i][0]
            dy = self.points[i + 1][1] - self.points[i][1]
            total += (dx ** 2 + dy ** 2) ** 0.5
        return total

    @property
    def start_point(self) -> Optional[Point2D]:
        return self.points[0] if self.points else None

    @property
    def end_point(self) -> Optional[Point2D]:
        return self.points[-1] if self.points else None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "points": self.points,
            "thickness": self.thickness,
            "height": self.height,
            "layer": self.layer,
            "is_exterior": self.is_exterior,
            "length": self.length,
        }


@dataclass
class Door:
    """Represents a door element in a floor plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    position: Point2D = (0.0, 0.0)
    width: float = 0.9  # meters
    height: float = 2.1  # meters
    swing: DoorSwing = DoorSwing.LEFT
    angle: float = 0.0  # rotation in degrees
    wall_id: Optional[str] = None
    layer: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": self.position,
            "width": self.width,
            "height": self.height,
            "swing": self.swing.value,
            "angle": self.angle,
            "wall_id": self.wall_id,
            "layer": self.layer,
        }


@dataclass
class Window:
    """Represents a window element in a floor plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    position: Point2D = (0.0, 0.0)
    width: float = 1.2  # meters
    height: float = 1.5  # meters
    sill_height: float = 0.9  # meters from floor
    window_type: WindowType = WindowType.SINGLE
    angle: float = 0.0  # rotation in degrees
    wall_id: Optional[str] = None
    layer: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": self.position,
            "width": self.width,
            "height": self.height,
            "sill_height": self.sill_height,
            "window_type": self.window_type.value,
            "angle": self.angle,
            "wall_id": self.wall_id,
            "layer": self.layer,
        }


@dataclass
class Room:
    """Represents a room/space in a floor plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    polygon: List[Point2D] = field(default_factory=list)
    floor_level: int = 0
    ceiling_height: float = 3.0
    room_type: str = "generic"  # living, bedroom, kitchen, bathroom, etc.

    @property
    def area(self) -> float:
        """Calculate room area using shoelace formula."""
        if len(self.polygon) < 3:
            return 0.0
        n = len(self.polygon)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.polygon[i][0] * self.polygon[j][1]
            area -= self.polygon[j][0] * self.polygon[i][1]
        return abs(area) / 2.0

    @property
    def perimeter(self) -> float:
        """Calculate room perimeter."""
        if len(self.polygon) < 2:
            return 0.0
        total = 0.0
        n = len(self.polygon)
        for i in range(n):
            j = (i + 1) % n
            dx = self.polygon[j][0] - self.polygon[i][0]
            dy = self.polygon[j][1] - self.polygon[i][1]
            total += (dx ** 2 + dy ** 2) ** 0.5
        return total

    @property
    def centroid(self) -> Point2D:
        """Calculate room centroid."""
        if not self.polygon:
            return (0.0, 0.0)
        x_sum = sum(p[0] for p in self.polygon)
        y_sum = sum(p[1] for p in self.polygon)
        n = len(self.polygon)
        return (x_sum / n, y_sum / n)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "polygon": self.polygon,
            "floor_level": self.floor_level,
            "ceiling_height": self.ceiling_height,
            "room_type": self.room_type,
            "area": round(self.area, 2),
            "perimeter": round(self.perimeter, 2),
            "centroid": self.centroid,
        }


@dataclass
class Dimension:
    """Represents a dimension annotation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start: Point2D = (0.0, 0.0)
    end: Point2D = (0.0, 0.0)
    value: float = 0.0
    unit: str = "m"
    text: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "value": self.value,
            "unit": self.unit,
            "text": self.text,
        }
