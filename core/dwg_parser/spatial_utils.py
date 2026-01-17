"""Spatial utility functions for geometry processing.

Uses Shapely for robust geometric operations.
"""

from typing import List, Tuple, Optional
from shapely.geometry import Point, Polygon as ShapelyPolygon, LineString
from shapely.validation import make_valid

Point2D = Tuple[float, float]


def point_in_polygon(point: Point2D, polygon: List[Point2D]) -> bool:
    """Check if a point is inside or on the boundary of a polygon.

    Args:
        point: (x, y) coordinates
        polygon: List of (x, y) vertices

    Returns:
        True if point is inside or on boundary
    """
    p = Point(point)
    poly = ShapelyPolygon(polygon)
    return poly.contains(p) or poly.boundary.contains(p)


def polygon_area(polygon: List[Point2D]) -> float:
    """Calculate the area of a polygon.

    Args:
        polygon: List of (x, y) vertices

    Returns:
        Area in square units (always positive)
    """
    if len(polygon) < 3:
        return 0.0
    poly = ShapelyPolygon(polygon)
    return abs(poly.area)


def polygon_centroid(polygon: List[Point2D]) -> Point2D:
    """Calculate the centroid of a polygon.

    Args:
        polygon: List of (x, y) vertices

    Returns:
        (x, y) coordinates of centroid
    """
    if len(polygon) < 3:
        if polygon:
            return polygon[0]
        return (0.0, 0.0)
    poly = ShapelyPolygon(polygon)
    c = poly.centroid
    return (c.x, c.y)


def segments_intersect(
    p1: Point2D, p2: Point2D, p3: Point2D, p4: Point2D
) -> bool:
    """Check if two line segments intersect.

    Args:
        p1, p2: Endpoints of first segment
        p3, p4: Endpoints of second segment

    Returns:
        True if segments intersect (including touching)
    """
    line1 = LineString([p1, p2])
    line2 = LineString([p3, p4])
    return line1.intersects(line2)


def find_intersection_point(
    p1: Point2D, p2: Point2D, p3: Point2D, p4: Point2D
) -> Optional[Point2D]:
    """Find the intersection point of two line segments.

    Args:
        p1, p2: Endpoints of first segment
        p3, p4: Endpoints of second segment

    Returns:
        (x, y) intersection point, or None if no intersection
    """
    line1 = LineString([p1, p2])
    line2 = LineString([p3, p4])
    intersection = line1.intersection(line2)

    if intersection.is_empty:
        return None
    if intersection.geom_type == 'Point':
        return (intersection.x, intersection.y)
    return None


def make_polygon_valid(polygon: List[Point2D]) -> List[Point2D]:
    """Fix a potentially invalid polygon (self-intersecting, etc.).

    Args:
        polygon: List of (x, y) vertices

    Returns:
        Valid polygon vertices
    """
    if len(polygon) < 3:
        return polygon
    poly = ShapelyPolygon(polygon)
    if not poly.is_valid:
        poly = make_valid(poly)
    if poly.geom_type == 'Polygon':
        return list(poly.exterior.coords)[:-1]
    return polygon


def distance(p1: Point2D, p2: Point2D) -> float:
    """Calculate Euclidean distance between two points."""
    return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
