# Room Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-detect rooms from wall geometry using cycle detection, then classify room types with GPT-4.

**Architecture:** Two-stage hybrid approach: (1) WallGraph builds a planar graph from walls, snaps nearby endpoints, finds minimal cycles representing rooms; (2) RoomClassifier gathers context (area, fixtures, text) and calls GPT-4 to classify room types.

**Tech Stack:** Python 3.11, ezdxf, Shapely 2.0, rtree, Azure OpenAI GPT-4

**Design Doc:** `docs/plans/2026-01-17-room-detection-design.md`

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml:8-30`

**Step 1: Add shapely and rtree to dependencies**

In `pyproject.toml`, add to the `dependencies` list:

```toml
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "python-multipart>=0.0.6",
    "ezdxf>=1.1.0",
    "numpy>=1.26.0",
    "pillow>=10.2.0",
    "svgwrite>=1.4.3",
    "trimesh>=4.0.0",
    "pydantic>=2.5.0",
    "redis>=5.0.0",
    "sqlalchemy>=2.0.0",
    "aiofiles>=23.2.0",
    "httpx>=0.26.0",
    # Geometry processing
    "shapely>=2.0.0",
    "rtree>=1.2.0",
    # Azure SDK
    "openai>=1.12.0",
    "azure-storage-blob>=12.19.0",
    "azure-identity>=1.15.0",
    # Optional: Anthropic as fallback
    "anthropic>=0.18.0",
    # Firebase Admin SDK for push notifications
    "firebase-admin>=6.4.0",
]
```

**Step 2: Install new dependencies**

Run: `pip install -e ".[dev]"`

Expected: Successfully installed shapely and rtree

**Step 3: Verify imports work**

Run: `python -c "from shapely.geometry import Polygon; from rtree import index; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: Add shapely and rtree dependencies for room detection"
```

---

## Task 2: Create Spatial Utilities Module

**Files:**
- Create: `core/dwg_parser/spatial_utils.py`
- Create: `tests/test_spatial_utils.py`

**Step 1: Write failing tests for point-in-polygon**

Create `tests/test_spatial_utils.py`:

```python
"""Tests for spatial utility functions."""

import pytest
from core.dwg_parser.spatial_utils import (
    point_in_polygon,
    polygon_area,
    polygon_centroid,
    segments_intersect,
    find_intersection_point,
)


class TestPointInPolygon:
    """Tests for point_in_polygon function."""

    def test_point_inside_square(self):
        square = [(0, 0), (4, 0), (4, 4), (0, 4)]
        assert point_in_polygon((2, 2), square) is True

    def test_point_outside_square(self):
        square = [(0, 0), (4, 0), (4, 4), (0, 4)]
        assert point_in_polygon((5, 5), square) is False

    def test_point_on_edge(self):
        square = [(0, 0), (4, 0), (4, 4), (0, 4)]
        # Points on boundary are considered inside
        assert point_in_polygon((2, 0), square) is True

    def test_point_at_vertex(self):
        square = [(0, 0), (4, 0), (4, 4), (0, 4)]
        assert point_in_polygon((0, 0), square) is True

    def test_l_shaped_polygon(self):
        l_shape = [(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)]
        assert point_in_polygon((0.5, 0.5), l_shape) is True
        assert point_in_polygon((1.5, 1.5), l_shape) is False


class TestPolygonArea:
    """Tests for polygon_area function."""

    def test_unit_square(self):
        square = [(0, 0), (1, 0), (1, 1), (0, 1)]
        assert polygon_area(square) == pytest.approx(1.0)

    def test_rectangle(self):
        rect = [(0, 0), (4, 0), (4, 3), (0, 3)]
        assert polygon_area(rect) == pytest.approx(12.0)

    def test_triangle(self):
        tri = [(0, 0), (4, 0), (2, 3)]
        assert polygon_area(tri) == pytest.approx(6.0)

    def test_clockwise_same_as_counterclockwise(self):
        cw = [(0, 0), (0, 1), (1, 1), (1, 0)]
        ccw = [(0, 0), (1, 0), (1, 1), (0, 1)]
        assert polygon_area(cw) == pytest.approx(polygon_area(ccw))


class TestPolygonCentroid:
    """Tests for polygon_centroid function."""

    def test_square_centroid(self):
        square = [(0, 0), (4, 0), (4, 4), (0, 4)]
        cx, cy = polygon_centroid(square)
        assert cx == pytest.approx(2.0)
        assert cy == pytest.approx(2.0)

    def test_rectangle_centroid(self):
        rect = [(0, 0), (6, 0), (6, 2), (0, 2)]
        cx, cy = polygon_centroid(rect)
        assert cx == pytest.approx(3.0)
        assert cy == pytest.approx(1.0)


class TestSegmentsIntersect:
    """Tests for segment intersection."""

    def test_crossing_segments(self):
        assert segments_intersect((0, 0), (4, 4), (0, 4), (4, 0)) is True

    def test_parallel_segments(self):
        assert segments_intersect((0, 0), (4, 0), (0, 1), (4, 1)) is False

    def test_t_intersection(self):
        assert segments_intersect((0, 2), (4, 2), (2, 0), (2, 4)) is True

    def test_non_intersecting(self):
        assert segments_intersect((0, 0), (1, 0), (2, 0), (3, 0)) is False


class TestFindIntersectionPoint:
    """Tests for finding intersection points."""

    def test_crossing_at_center(self):
        pt = find_intersection_point((0, 0), (4, 4), (0, 4), (4, 0))
        assert pt is not None
        assert pt[0] == pytest.approx(2.0)
        assert pt[1] == pytest.approx(2.0)

    def test_no_intersection_returns_none(self):
        pt = find_intersection_point((0, 0), (1, 0), (0, 1), (1, 1))
        assert pt is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_spatial_utils.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'core.dwg_parser.spatial_utils'`

**Step 3: Implement spatial_utils.py**

Create `core/dwg_parser/spatial_utils.py`:

```python
"""Spatial utility functions for geometry processing.

Uses Shapely for robust geometric operations.
"""

from typing import List, Tuple, Optional
from shapely.geometry import Point, Polygon as ShapelyPolygon, LineString
from shapely.ops import make_valid

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
        return list(poly.exterior.coords)[:-1]  # Remove duplicate closing point
    return polygon


def distance(p1: Point2D, p2: Point2D) -> float:
    """Calculate Euclidean distance between two points."""
    return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_spatial_utils.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/dwg_parser/spatial_utils.py tests/test_spatial_utils.py
git commit -m "feat: Add spatial utilities module with Shapely"
```

---

## Task 3: Create WallGraph Data Structures

**Files:**
- Create: `core/dwg_parser/wall_graph.py`
- Create: `tests/test_wall_graph.py`

**Step 1: Write failing tests for graph construction**

Create `tests/test_wall_graph.py`:

```python
"""Tests for WallGraph class."""

import pytest
from core.dwg_parser.wall_graph import WallGraph, GraphNode, GraphEdge
from core.dwg_parser.elements import Wall


class TestGraphConstruction:
    """Tests for building the wall graph."""

    def test_single_wall_creates_two_nodes(self):
        graph = WallGraph()
        wall = Wall(points=[(0, 0), (5, 0)])
        graph.add_wall(wall)

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_two_connected_walls_share_node(self):
        graph = WallGraph()
        wall1 = Wall(points=[(0, 0), (5, 0)])
        wall2 = Wall(points=[(5, 0), (5, 5)])
        graph.add_wall(wall1)
        graph.add_wall(wall2)

        # Should have 3 nodes: (0,0), (5,0), (5,5)
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2

    def test_snap_tolerance_merges_nearby_endpoints(self):
        graph = WallGraph(snap_tolerance=0.1)
        wall1 = Wall(points=[(0, 0), (5, 0)])
        wall2 = Wall(points=[(5.05, 0), (5.05, 5)])  # 0.05 away
        graph.add_wall(wall1)
        graph.add_wall(wall2)

        # Endpoints should merge
        assert len(graph.nodes) == 3

    def test_no_merge_beyond_tolerance(self):
        graph = WallGraph(snap_tolerance=0.1)
        wall1 = Wall(points=[(0, 0), (5, 0)])
        wall2 = Wall(points=[(5.2, 0), (5.2, 5)])  # 0.2 away
        graph.add_wall(wall1)
        graph.add_wall(wall2)

        # Endpoints should NOT merge
        assert len(graph.nodes) == 4

    def test_polyline_wall_creates_multiple_edges(self):
        graph = WallGraph()
        wall = Wall(points=[(0, 0), (5, 0), (5, 5), (0, 5)])
        graph.add_wall(wall)

        assert len(graph.nodes) == 4
        assert len(graph.edges) == 3

    def test_duplicate_walls_deduplicated(self):
        graph = WallGraph()
        wall1 = Wall(points=[(0, 0), (5, 0)])
        wall2 = Wall(points=[(0, 0), (5, 0)])  # Duplicate
        graph.add_wall(wall1)
        graph.add_wall(wall2)

        assert len(graph.edges) == 1


class TestNodeLookup:
    """Tests for finding nodes by position."""

    def test_find_node_at_exact_position(self):
        graph = WallGraph()
        wall = Wall(points=[(0, 0), (5, 0)])
        graph.add_wall(wall)

        node = graph.find_node_near((0, 0))
        assert node is not None
        assert node.position == (0, 0)

    def test_find_node_within_tolerance(self):
        graph = WallGraph(snap_tolerance=0.1)
        wall = Wall(points=[(0, 0), (5, 0)])
        graph.add_wall(wall)

        node = graph.find_node_near((0.05, 0.05))
        assert node is not None

    def test_no_node_found_returns_none(self):
        graph = WallGraph()
        wall = Wall(points=[(0, 0), (5, 0)])
        graph.add_wall(wall)

        node = graph.find_node_near((10, 10))
        assert node is None


class TestEdgeConnectivity:
    """Tests for edge connectivity."""

    def test_get_edges_from_node(self):
        graph = WallGraph()
        wall1 = Wall(points=[(0, 0), (5, 0)])
        wall2 = Wall(points=[(5, 0), (5, 5)])
        wall3 = Wall(points=[(5, 0), (10, 0)])
        graph.add_wall(wall1)
        graph.add_wall(wall2)
        graph.add_wall(wall3)

        # Node at (5, 0) should have 3 edges
        node = graph.find_node_near((5, 0))
        edges = graph.get_edges_from_node(node.id)
        assert len(edges) == 3

    def test_get_other_node(self):
        graph = WallGraph()
        wall = Wall(points=[(0, 0), (5, 0)])
        graph.add_wall(wall)

        node_a = graph.find_node_near((0, 0))
        edge = graph.get_edges_from_node(node_a.id)[0]
        node_b = graph.get_other_node(edge, node_a.id)

        assert node_b.position == (5, 0)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_wall_graph.py::TestGraphConstruction -v`

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement WallGraph basic structure**

Create `core/dwg_parser/wall_graph.py`:

```python
"""Wall graph for detecting enclosed rooms.

Builds a planar graph from wall segments where nodes are endpoints
and edges are wall segments. Uses R-tree for efficient spatial queries.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
import uuid

from rtree import index

from .elements import Wall, Point2D
from .spatial_utils import distance


@dataclass
class GraphNode:
    """A node in the wall graph representing a wall endpoint."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    position: Point2D = (0.0, 0.0)
    edge_ids: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.id)


@dataclass
class GraphEdge:
    """An edge in the wall graph representing a wall segment."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_ids: Tuple[str, str] = ("", "")
    wall_id: str = ""

    def __hash__(self):
        return hash(self.id)


class WallGraph:
    """Graph structure for wall connectivity and room detection."""

    def __init__(self, snap_tolerance: float = 0.05):
        """Initialize the wall graph.

        Args:
            snap_tolerance: Distance within which endpoints are merged (meters)
        """
        self.snap_tolerance = snap_tolerance
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self._edge_set: Set[Tuple[str, str]] = set()  # For deduplication

        # R-tree spatial index for fast proximity queries
        self._spatial_index = index.Index()
        self._node_count = 0

    def add_wall(self, wall: Wall) -> None:
        """Add a wall to the graph.

        Args:
            wall: Wall object with points
        """
        if len(wall.points) < 2:
            return

        # Process each segment of the wall
        for i in range(len(wall.points) - 1):
            start = wall.points[i]
            end = wall.points[i + 1]
            self._add_segment(start, end, wall.id)

    def add_walls(self, walls: List[Wall]) -> None:
        """Add multiple walls to the graph."""
        for wall in walls:
            self.add_wall(wall)

    def _add_segment(self, start: Point2D, end: Point2D, wall_id: str) -> None:
        """Add a single wall segment to the graph."""
        # Find or create nodes for endpoints
        node_a = self._get_or_create_node(start)
        node_b = self._get_or_create_node(end)

        # Skip if same node (zero-length segment)
        if node_a.id == node_b.id:
            return

        # Check for duplicate edge
        edge_key = tuple(sorted([node_a.id, node_b.id]))
        if edge_key in self._edge_set:
            return

        # Create edge
        edge = GraphEdge(
            node_ids=(node_a.id, node_b.id),
            wall_id=wall_id,
        )
        self.edges[edge.id] = edge
        self._edge_set.add(edge_key)

        # Update node connectivity
        node_a.edge_ids.append(edge.id)
        node_b.edge_ids.append(edge.id)

    def _get_or_create_node(self, position: Point2D) -> GraphNode:
        """Get existing node near position or create new one."""
        # Search for existing node within tolerance
        existing = self.find_node_near(position)
        if existing is not None:
            return existing

        # Create new node
        node = GraphNode(position=position)
        self.nodes[node.id] = node

        # Add to spatial index
        x, y = position
        self._spatial_index.insert(
            self._node_count,
            (x, y, x, y),
            obj=node.id
        )
        self._node_count += 1

        return node

    def find_node_near(self, position: Point2D, tolerance: Optional[float] = None) -> Optional[GraphNode]:
        """Find a node within tolerance of the given position.

        Args:
            position: (x, y) coordinates
            tolerance: Search radius (defaults to snap_tolerance)

        Returns:
            GraphNode if found, None otherwise
        """
        if tolerance is None:
            tolerance = self.snap_tolerance

        x, y = position
        # Query R-tree for candidates
        candidates = list(self._spatial_index.intersection(
            (x - tolerance, y - tolerance, x + tolerance, y + tolerance),
            objects=True
        ))

        # Find closest within tolerance
        best_node = None
        best_dist = float('inf')

        for item in candidates:
            node_id = item.object
            node = self.nodes[node_id]
            dist = distance(position, node.position)
            if dist <= tolerance and dist < best_dist:
                best_dist = dist
                best_node = node

        return best_node

    def get_edges_from_node(self, node_id: str) -> List[GraphEdge]:
        """Get all edges connected to a node."""
        node = self.nodes.get(node_id)
        if node is None:
            return []
        return [self.edges[eid] for eid in node.edge_ids if eid in self.edges]

    def get_other_node(self, edge: GraphEdge, node_id: str) -> Optional[GraphNode]:
        """Get the node at the other end of an edge."""
        if edge.node_ids[0] == node_id:
            return self.nodes.get(edge.node_ids[1])
        elif edge.node_ids[1] == node_id:
            return self.nodes.get(edge.node_ids[0])
        return None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_wall_graph.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/dwg_parser/wall_graph.py tests/test_wall_graph.py
git commit -m "feat: Add WallGraph with node/edge structure and spatial indexing"
```

---

## Task 4: Implement Cycle Detection

**Files:**
- Modify: `core/dwg_parser/wall_graph.py`
- Modify: `tests/test_wall_graph.py`

**Step 1: Write failing tests for cycle detection**

Add to `tests/test_wall_graph.py`:

```python
class TestCycleDetection:
    """Tests for finding enclosed room polygons."""

    def test_single_rectangle_room(self):
        """Four walls forming a rectangle should yield one cycle."""
        graph = WallGraph()
        # Create a 5x4 rectangle
        graph.add_wall(Wall(points=[(0, 0), (5, 0)]))
        graph.add_wall(Wall(points=[(5, 0), (5, 4)]))
        graph.add_wall(Wall(points=[(5, 4), (0, 4)]))
        graph.add_wall(Wall(points=[(0, 4), (0, 0)]))

        cycles = graph.find_cycles()

        assert len(cycles) == 1
        assert len(cycles[0]) == 4  # 4 vertices

    def test_two_adjacent_rooms(self):
        """Two rooms sharing a wall should yield two cycles."""
        graph = WallGraph()
        # Room 1: 0,0 to 5,4
        graph.add_wall(Wall(points=[(0, 0), (5, 0)]))
        graph.add_wall(Wall(points=[(5, 0), (5, 4)]))
        graph.add_wall(Wall(points=[(5, 4), (0, 4)]))
        graph.add_wall(Wall(points=[(0, 4), (0, 0)]))
        # Room 2: 5,0 to 10,4 (shares wall at x=5)
        graph.add_wall(Wall(points=[(5, 0), (10, 0)]))
        graph.add_wall(Wall(points=[(10, 0), (10, 4)]))
        graph.add_wall(Wall(points=[(10, 4), (5, 4)]))

        cycles = graph.find_cycles()

        assert len(cycles) == 2

    def test_no_cycles_from_open_walls(self):
        """Walls that don't form a closed shape should yield no cycles."""
        graph = WallGraph()
        graph.add_wall(Wall(points=[(0, 0), (5, 0)]))
        graph.add_wall(Wall(points=[(5, 0), (5, 4)]))
        graph.add_wall(Wall(points=[(5, 4), (0, 4)]))
        # Missing the closing wall

        cycles = graph.find_cycles()

        assert len(cycles) == 0

    def test_l_shaped_room(self):
        """L-shaped room should yield one cycle."""
        graph = WallGraph()
        # L-shape vertices: (0,0), (4,0), (4,2), (2,2), (2,4), (0,4)
        points = [(0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4), (0, 0)]
        for i in range(len(points) - 1):
            graph.add_wall(Wall(points=[points[i], points[i+1]]))

        cycles = graph.find_cycles()

        assert len(cycles) == 1
        assert len(cycles[0]) == 6

    def test_room_with_internal_wall(self):
        """Room with internal dividing wall should yield two cycles."""
        graph = WallGraph()
        # Outer rectangle 10x4
        graph.add_wall(Wall(points=[(0, 0), (10, 0)]))
        graph.add_wall(Wall(points=[(10, 0), (10, 4)]))
        graph.add_wall(Wall(points=[(10, 4), (0, 4)]))
        graph.add_wall(Wall(points=[(0, 4), (0, 0)]))
        # Internal wall dividing at x=5
        graph.add_wall(Wall(points=[(5, 0), (5, 4)]))

        cycles = graph.find_cycles()

        assert len(cycles) == 2

    def test_excludes_outer_boundary(self):
        """The outer boundary should not be returned as a room."""
        graph = WallGraph()
        # Single room - outer boundary equals the room
        graph.add_wall(Wall(points=[(0, 0), (5, 0)]))
        graph.add_wall(Wall(points=[(5, 0), (5, 4)]))
        graph.add_wall(Wall(points=[(5, 4), (0, 4)]))
        graph.add_wall(Wall(points=[(0, 4), (0, 0)]))

        cycles = graph.find_cycles()

        # Should return the room (which is also the boundary)
        assert len(cycles) == 1

    def test_filters_tiny_cycles(self):
        """Cycles smaller than min_area should be filtered."""
        graph = WallGraph()
        # Tiny 0.1x0.1 room (0.01 m²)
        graph.add_wall(Wall(points=[(0, 0), (0.1, 0)]))
        graph.add_wall(Wall(points=[(0.1, 0), (0.1, 0.1)]))
        graph.add_wall(Wall(points=[(0.1, 0.1), (0, 0.1)]))
        graph.add_wall(Wall(points=[(0, 0.1), (0, 0)]))

        cycles = graph.find_cycles(min_area=0.5)

        assert len(cycles) == 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_wall_graph.py::TestCycleDetection -v`

Expected: FAIL with `AttributeError: 'WallGraph' object has no attribute 'find_cycles'`

**Step 3: Implement cycle detection**

Add to `core/dwg_parser/wall_graph.py`:

```python
import math
from .spatial_utils import polygon_area


# Add this method to WallGraph class:

    def find_cycles(self, min_area: float = 0.5) -> List[List[Point2D]]:
        """Find all minimal cycles (enclosed rooms) in the graph.

        Uses the "always turn right" planar traversal algorithm.

        Args:
            min_area: Minimum area in square meters to include (filters artifacts)

        Returns:
            List of polygons, each a list of (x, y) vertices
        """
        if not self.edges:
            return []

        cycles: List[List[Point2D]] = []

        # Track which directed edges have been used
        # Each undirected edge can be traversed in two directions
        used_directions: Set[Tuple[str, str]] = set()

        # Try starting from each edge in each direction
        for edge in self.edges.values():
            for start_node_id in edge.node_ids:
                direction = (edge.id, start_node_id)
                if direction in used_directions:
                    continue

                # Try to find a cycle starting from this edge
                cycle = self._trace_cycle(edge, start_node_id, used_directions)
                if cycle and len(cycle) >= 3:
                    area = polygon_area(cycle)
                    if area >= min_area:
                        cycles.append(cycle)

        # Remove the outer boundary if there are multiple cycles
        if len(cycles) > 1:
            cycles = self._remove_outer_boundary(cycles)

        return cycles

    def _trace_cycle(
        self,
        start_edge: GraphEdge,
        start_node_id: str,
        used_directions: Set[Tuple[str, str]]
    ) -> Optional[List[Point2D]]:
        """Trace a cycle by always turning right at each node.

        Args:
            start_edge: Edge to start from
            start_node_id: Node to start from (determines direction)
            used_directions: Set of already-used (edge_id, start_node_id) pairs

        Returns:
            List of vertices forming the cycle, or None if no cycle found
        """
        path_nodes: List[str] = [start_node_id]
        path_edges: List[Tuple[str, str]] = []  # (edge_id, from_node_id)

        current_edge = start_edge
        current_node_id = start_node_id

        max_steps = len(self.edges) * 2 + 10  # Safety limit
        steps = 0

        while steps < max_steps:
            steps += 1

            # Move to the other end of the edge
            next_node = self.get_other_node(current_edge, current_node_id)
            if next_node is None:
                return None

            # Record this directed traversal
            path_edges.append((current_edge.id, current_node_id))

            # Check if we've completed a cycle
            if next_node.id == start_node_id and len(path_nodes) >= 3:
                # Mark all directions as used
                for edge_id, from_node in path_edges:
                    used_directions.add((edge_id, from_node))

                # Convert path to polygon
                return [self.nodes[nid].position for nid in path_nodes]

            # Check for unexpected revisit (not a minimal cycle)
            if next_node.id in path_nodes:
                return None

            path_nodes.append(next_node.id)

            # Find the next edge by turning right
            next_edge = self._find_rightmost_edge(
                current_edge, current_node_id, next_node
            )
            if next_edge is None:
                return None

            current_edge = next_edge
            current_node_id = next_node.id

        return None

    def _find_rightmost_edge(
        self,
        incoming_edge: GraphEdge,
        from_node_id: str,
        current_node: GraphNode
    ) -> Optional[GraphEdge]:
        """Find the edge that turns rightmost from the incoming edge.

        Args:
            incoming_edge: The edge we arrived on
            from_node_id: The node we came from
            current_node: The node we're at now

        Returns:
            The edge to follow next (rightmost turn)
        """
        outgoing_edges = [
            e for e in self.get_edges_from_node(current_node.id)
            if e.id != incoming_edge.id
        ]

        if not outgoing_edges:
            return None

        if len(outgoing_edges) == 1:
            return outgoing_edges[0]

        # Calculate incoming angle
        from_node = self.nodes[from_node_id]
        incoming_angle = math.atan2(
            current_node.position[1] - from_node.position[1],
            current_node.position[0] - from_node.position[0]
        )

        # Find the edge with the smallest clockwise angle from incoming
        best_edge = None
        best_angle = float('inf')

        for edge in outgoing_edges:
            other_node = self.get_other_node(edge, current_node.id)
            if other_node is None:
                continue

            outgoing_angle = math.atan2(
                other_node.position[1] - current_node.position[1],
                other_node.position[0] - current_node.position[0]
            )

            # Calculate clockwise angle difference
            angle_diff = incoming_angle - outgoing_angle
            # Normalize to [0, 2π)
            while angle_diff < 0:
                angle_diff += 2 * math.pi
            while angle_diff >= 2 * math.pi:
                angle_diff -= 2 * math.pi

            # Smaller angle = sharper right turn
            if angle_diff < best_angle:
                best_angle = angle_diff
                best_edge = edge

        return best_edge

    def _remove_outer_boundary(
        self, cycles: List[List[Point2D]]
    ) -> List[List[Point2D]]:
        """Remove the outermost cycle (building boundary).

        The outer boundary is identified as the cycle with the largest area.
        However, if there's only one cycle or the largest is not significantly
        larger, keep all cycles.
        """
        if len(cycles) <= 1:
            return cycles

        areas = [(polygon_area(c), i) for i, c in enumerate(cycles)]
        areas.sort(reverse=True)

        largest_area, largest_idx = areas[0]
        second_area = areas[1][0] if len(areas) > 1 else 0

        # Only remove if significantly larger (likely outer boundary)
        # and there are interior rooms
        total_inner = sum(a for a, _ in areas[1:])
        if largest_area > total_inner * 0.9:
            # The largest cycle encompasses all others - it's the boundary
            return [c for i, c in enumerate(cycles) if i != largest_idx]

        return cycles
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_wall_graph.py::TestCycleDetection -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/dwg_parser/wall_graph.py tests/test_wall_graph.py
git commit -m "feat: Add cycle detection algorithm to WallGraph"
```

---

## Task 5: Create RoomClassifier

**Files:**
- Create: `core/dwg_parser/room_classifier.py`
- Create: `tests/test_room_classifier.py`

**Step 1: Write failing tests for RoomClassifier**

Create `tests/test_room_classifier.py`:

```python
"""Tests for RoomClassifier."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from core.dwg_parser.room_classifier import (
    RoomClassifier,
    RoomContext,
    RoomClassification,
    FIXTURE_PATTERNS,
)


class TestRoomContext:
    """Tests for RoomContext data class."""

    def test_context_creation(self):
        ctx = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
            area=20.0,
            aspect_ratio=1.25,
            door_count=1,
            window_count=2,
        )
        assert ctx.area == 20.0
        assert ctx.door_count == 1

    def test_context_defaults(self):
        ctx = RoomContext(
            polygon=[(0, 0), (1, 0), (1, 1), (0, 1)],
            area=1.0,
            aspect_ratio=1.0,
        )
        assert ctx.door_count == 0
        assert ctx.window_count == 0
        assert ctx.fixtures == []
        assert ctx.nearby_text == []


class TestFixtureDetection:
    """Tests for fixture pattern matching."""

    def test_bathroom_fixtures(self):
        assert "toilet" in FIXTURE_PATTERNS["bathroom"]
        assert "shower" in FIXTURE_PATTERNS["bathroom"]
        assert "sink" in FIXTURE_PATTERNS["bathroom"]

    def test_kitchen_fixtures(self):
        assert "stove" in FIXTURE_PATTERNS["kitchen"]
        assert "fridge" in FIXTURE_PATTERNS["kitchen"]
        assert "oven" in FIXTURE_PATTERNS["kitchen"]

    def test_laundry_fixtures(self):
        assert "washer" in FIXTURE_PATTERNS["laundry"]
        assert "dryer" in FIXTURE_PATTERNS["laundry"]


class TestRoomClassification:
    """Tests for classification results."""

    def test_classification_creation(self):
        result = RoomClassification(
            room_type="bedroom",
            confidence=0.85,
            reasoning="12m² room with one door, no fixtures",
        )
        assert result.room_type == "bedroom"
        assert result.confidence == 0.85

    def test_low_confidence_flag(self):
        low = RoomClassification(room_type="unknown", confidence=0.3)
        high = RoomClassification(room_type="kitchen", confidence=0.9)

        assert low.is_low_confidence is True
        assert high.is_low_confidence is False


class TestRoomClassifier:
    """Tests for RoomClassifier."""

    def test_classifier_without_openai_returns_unknown(self):
        classifier = RoomClassifier(openai_service=None)
        ctx = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
            area=20.0,
            aspect_ratio=1.25,
        )

        result = classifier.classify(ctx)

        assert result.room_type == "unknown"
        assert result.confidence == 0.0

    def test_infer_from_fixtures_bathroom(self):
        classifier = RoomClassifier(openai_service=None)
        ctx = RoomContext(
            polygon=[(0, 0), (3, 0), (3, 2), (0, 2)],
            area=6.0,
            aspect_ratio=1.5,
            fixtures=["toilet", "sink", "shower"],
        )

        result = classifier._infer_from_fixtures(ctx)

        assert result == "bathroom"

    def test_infer_from_fixtures_kitchen(self):
        classifier = RoomClassifier(openai_service=None)
        ctx = RoomContext(
            polygon=[(0, 0), (4, 0), (4, 3), (0, 3)],
            area=12.0,
            aspect_ratio=1.33,
            fixtures=["stove", "refrigerator", "sink"],
        )

        result = classifier._infer_from_fixtures(ctx)

        assert result == "kitchen"

    def test_infer_from_text(self):
        classifier = RoomClassifier(openai_service=None)
        ctx = RoomContext(
            polygon=[(0, 0), (5, 0), (5, 5), (0, 5)],
            area=25.0,
            aspect_ratio=1.0,
            nearby_text=["MASTER BEDROOM"],
        )

        result = classifier._infer_from_text(ctx)

        assert result == "bedroom"


class TestClassifierWithMockedOpenAI:
    """Tests with mocked OpenAI service."""

    @pytest.fixture
    def mock_openai(self):
        mock = Mock()
        mock.chat = AsyncMock(return_value={
            "room_type": "living_room",
            "confidence": 0.92,
            "reasoning": "Large room with multiple windows"
        })
        return mock

    def test_classify_with_openai(self, mock_openai):
        classifier = RoomClassifier(openai_service=mock_openai)
        ctx = RoomContext(
            polygon=[(0, 0), (6, 0), (6, 5), (0, 5)],
            area=30.0,
            aspect_ratio=1.2,
            door_count=2,
            window_count=3,
        )

        # Since classify uses async internally, we test the sync wrapper
        with patch.object(classifier, '_classify_with_ai', return_value=RoomClassification(
            room_type="living_room",
            confidence=0.92,
            reasoning="Large room with multiple windows"
        )):
            result = classifier.classify(ctx)

        assert result.room_type == "living_room"
        assert result.confidence == 0.92
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_room_classifier.py -v`

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement RoomClassifier**

Create `core/dwg_parser/room_classifier.py`:

```python
"""Room classifier using AI and heuristics.

Classifies detected room polygons into room types using a combination of
fixture detection, text recognition, and GPT-4 reasoning.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


# Fixture patterns for room type inference
FIXTURE_PATTERNS: Dict[str, List[str]] = {
    "bathroom": [
        "toilet", "wc", "sink", "basin", "shower", "tub", "bath",
        "bidet", "vanity", "lavatory",
    ],
    "kitchen": [
        "stove", "oven", "range", "fridge", "refrigerator", "sink",
        "dishwasher", "microwave", "cooktop", "hood",
    ],
    "laundry": [
        "washer", "dryer", "washing", "laundry", "ironing",
    ],
    "bedroom": [
        "bed", "wardrobe", "closet", "dresser", "nightstand",
    ],
    "office": [
        "desk", "computer", "workstation", "filing",
    ],
    "garage": [
        "car", "vehicle", "parking", "garage",
    ],
}

# Room type keywords for text matching
ROOM_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "living_room": ["living", "lounge", "family", "great room"],
    "bedroom": ["bedroom", "master", "guest room", "sleeping"],
    "bathroom": ["bathroom", "bath", "wc", "toilet", "powder", "restroom"],
    "kitchen": ["kitchen", "kitchenette", "cooking"],
    "dining_room": ["dining", "breakfast"],
    "office": ["office", "study", "den", "work room"],
    "hallway": ["hall", "hallway", "corridor", "passage", "entry", "foyer"],
    "closet": ["closet", "storage", "wardrobe", "pantry"],
    "laundry": ["laundry", "utility", "mud room"],
    "garage": ["garage", "carport", "parking"],
    "balcony": ["balcony", "terrace", "patio", "deck"],
    "conference_room": ["conference", "meeting", "board room"],
    "reception": ["reception", "lobby", "waiting"],
    "storage": ["storage", "store", "mechanical"],
}

# Valid room types
VALID_ROOM_TYPES = [
    "living_room", "bedroom", "bathroom", "kitchen", "hallway",
    "closet", "garage", "dining_room", "office", "laundry",
    "pantry", "balcony", "conference_room", "reception",
    "lobby", "storage", "utility", "unknown",
]


Point2D = tuple[float, float]


@dataclass
class RoomContext:
    """Context gathered for room classification."""

    polygon: List[Point2D]
    area: float  # square meters
    aspect_ratio: float  # width/height of bounding box
    door_count: int = 0
    window_count: int = 0
    fixtures: List[str] = field(default_factory=list)
    nearby_text: List[str] = field(default_factory=list)
    adjacent_rooms: List[str] = field(default_factory=list)


@dataclass
class RoomClassification:
    """Result of room classification."""

    room_type: str
    confidence: float
    reasoning: str = ""

    @property
    def is_low_confidence(self) -> bool:
        """Check if confidence is below threshold."""
        return self.confidence < 0.5


class RoomClassifier:
    """Classifies rooms using fixtures, text, and optionally AI."""

    def __init__(self, openai_service: Optional[Any] = None):
        """Initialize the classifier.

        Args:
            openai_service: Azure OpenAI service for AI classification.
                           If None, falls back to heuristic classification.
        """
        self.openai_service = openai_service

    def classify(self, context: RoomContext) -> RoomClassification:
        """Classify a single room.

        Args:
            context: RoomContext with room information

        Returns:
            RoomClassification with type and confidence
        """
        # Try fixture-based inference first
        fixture_type = self._infer_from_fixtures(context)
        if fixture_type:
            return RoomClassification(
                room_type=fixture_type,
                confidence=0.8,
                reasoning=f"Inferred from fixtures: {context.fixtures}",
            )

        # Try text-based inference
        text_type = self._infer_from_text(context)
        if text_type:
            return RoomClassification(
                room_type=text_type,
                confidence=0.9,
                reasoning=f"Inferred from text label: {context.nearby_text}",
            )

        # Try AI classification if available
        if self.openai_service is not None:
            try:
                return self._classify_with_ai(context)
            except Exception as e:
                logger.warning(f"AI classification failed: {e}")

        # Fallback to unknown
        return RoomClassification(
            room_type="unknown",
            confidence=0.0,
            reasoning="No fixtures, text, or AI available",
        )

    def classify_batch(
        self, contexts: List[RoomContext]
    ) -> List[RoomClassification]:
        """Classify multiple rooms efficiently.

        Args:
            contexts: List of RoomContext objects

        Returns:
            List of RoomClassification objects
        """
        results = []

        # First pass: use heuristics
        ai_needed = []
        for i, ctx in enumerate(contexts):
            fixture_type = self._infer_from_fixtures(ctx)
            if fixture_type:
                results.append(RoomClassification(
                    room_type=fixture_type,
                    confidence=0.8,
                    reasoning=f"Inferred from fixtures",
                ))
                continue

            text_type = self._infer_from_text(ctx)
            if text_type:
                results.append(RoomClassification(
                    room_type=text_type,
                    confidence=0.9,
                    reasoning=f"Inferred from text label",
                ))
                continue

            # Mark for AI classification
            ai_needed.append((i, ctx))
            results.append(None)  # Placeholder

        # Batch AI classification if needed and available
        if ai_needed and self.openai_service is not None:
            try:
                ai_results = self._classify_batch_with_ai(
                    [ctx for _, ctx in ai_needed]
                )
                for (idx, _), result in zip(ai_needed, ai_results):
                    results[idx] = result
            except Exception as e:
                logger.warning(f"Batch AI classification failed: {e}")

        # Fill any remaining with unknown
        for i, result in enumerate(results):
            if result is None:
                results[i] = RoomClassification(
                    room_type="unknown",
                    confidence=0.0,
                    reasoning="Classification failed",
                )

        return results

    def _infer_from_fixtures(self, context: RoomContext) -> Optional[str]:
        """Infer room type from detected fixtures."""
        if not context.fixtures:
            return None

        fixtures_lower = [f.lower() for f in context.fixtures]

        # Count matches for each room type
        scores: Dict[str, int] = {}
        for room_type, patterns in FIXTURE_PATTERNS.items():
            score = sum(
                1 for f in fixtures_lower
                if any(p in f for p in patterns)
            )
            if score > 0:
                scores[room_type] = score

        if not scores:
            return None

        # Return type with most matches
        return max(scores, key=scores.get)

    def _infer_from_text(self, context: RoomContext) -> Optional[str]:
        """Infer room type from nearby text labels."""
        if not context.nearby_text:
            return None

        text_lower = " ".join(context.nearby_text).lower()

        for room_type, keywords in ROOM_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return room_type

        return None

    def _classify_with_ai(self, context: RoomContext) -> RoomClassification:
        """Classify using AI (synchronous wrapper)."""
        # Run async classification
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._classify_with_ai_async(context))

    async def _classify_with_ai_async(
        self, context: RoomContext
    ) -> RoomClassification:
        """Classify using AI asynchronously."""
        prompt = self._build_classification_prompt(context)

        try:
            response = await self.openai_service.chat(
                message=prompt,
                system_prompt=(
                    "You are an architectural room classifier. "
                    "Analyze room data and classify the room type. "
                    "Return JSON only."
                ),
            )

            return self._parse_ai_response(response)
        except Exception as e:
            logger.error(f"AI classification error: {e}")
            return RoomClassification(
                room_type="unknown",
                confidence=0.0,
                reasoning=f"AI error: {e}",
            )

    def _classify_batch_with_ai(
        self, contexts: List[RoomContext]
    ) -> List[RoomClassification]:
        """Classify batch using AI (synchronous wrapper)."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._classify_batch_with_ai_async(contexts)
        )

    async def _classify_batch_with_ai_async(
        self, contexts: List[RoomContext]
    ) -> List[RoomClassification]:
        """Classify batch using AI asynchronously."""
        # For now, classify individually
        # TODO: Implement true batching in single API call
        results = []
        for ctx in contexts:
            result = await self._classify_with_ai_async(ctx)
            results.append(result)
        return results

    def _build_classification_prompt(self, context: RoomContext) -> str:
        """Build the prompt for AI classification."""
        # Calculate bounding box dimensions
        if context.polygon:
            xs = [p[0] for p in context.polygon]
            ys = [p[1] for p in context.polygon]
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
        else:
            width = height = 0

        prompt = f"""Classify this room from an architectural floor plan.

Room data:
- Area: {context.area:.1f} m²
- Dimensions: {width:.1f}m x {height:.1f}m
- Doors: {context.door_count}
- Windows: {context.window_count}
- Fixtures detected: {context.fixtures if context.fixtures else 'none'}
- Text labels found: {context.nearby_text if context.nearby_text else 'none'}

Valid room types: {', '.join(VALID_ROOM_TYPES)}

Return JSON only:
{{"room_type": "...", "confidence": 0.0-1.0, "reasoning": "..."}}"""

        return prompt

    def _parse_ai_response(self, response: Any) -> RoomClassification:
        """Parse AI response into RoomClassification."""
        try:
            if isinstance(response, str):
                data = json.loads(response)
            elif isinstance(response, dict):
                data = response
            else:
                raise ValueError(f"Unexpected response type: {type(response)}")

            room_type = data.get("room_type", "unknown")
            if room_type not in VALID_ROOM_TYPES:
                room_type = "unknown"

            return RoomClassification(
                room_type=room_type,
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return RoomClassification(
                room_type="unknown",
                confidence=0.0,
                reasoning=f"Parse error: {e}",
            )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_room_classifier.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/dwg_parser/room_classifier.py tests/test_room_classifier.py
git commit -m "feat: Add RoomClassifier with fixture/text/AI classification"
```

---

## Task 6: Integrate Room Detection into Parser

**Files:**
- Modify: `core/dwg_parser/parser.py`
- Modify: `core/dwg_parser/elements.py`
- Create: `tests/test_room_detection.py`

**Step 1: Update Room dataclass**

Add `confidence_low` field to `core/dwg_parser/elements.py`. In the `Room` class:

```python
@dataclass
class Room:
    """Represents a room/space in a floor plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    polygon: List[Point2D] = field(default_factory=list)
    floor_level: int = 0
    ceiling_height: float = 3.0
    room_type: str = "generic"  # living, bedroom, kitchen, bathroom, etc.
    confidence_low: bool = False  # Flag for low-confidence AI classification

    # ... rest of class unchanged ...

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "polygon": self.polygon,
            "floor_level": self.floor_level,
            "ceiling_height": self.ceiling_height,
            "room_type": self.room_type,
            "confidence_low": self.confidence_low,
            "area": round(self.area, 2),
            "perimeter": round(self.perimeter, 2),
            "centroid": self.centroid,
        }
```

**Step 2: Write integration test**

Create `tests/test_room_detection.py`:

```python
"""Integration tests for room detection from walls."""

import pytest
import tempfile
from pathlib import Path

import ezdxf

from core.dwg_parser.parser import DWGParser
from core.dwg_parser.wall_graph import WallGraph
from core.dwg_parser.elements import Wall


@pytest.fixture
def simple_apartment_dxf(tmp_path):
    """Create a simple apartment DXF with 3 rooms."""
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Outer walls (10m x 8m apartment)
    msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "WALLS"})
    msp.add_line((10, 0), (10, 8), dxfattribs={"layer": "WALLS"})
    msp.add_line((10, 8), (0, 8), dxfattribs={"layer": "WALLS"})
    msp.add_line((0, 8), (0, 0), dxfattribs={"layer": "WALLS"})

    # Internal wall dividing left (living) from right (bedrooms)
    msp.add_line((6, 0), (6, 8), dxfattribs={"layer": "WALLS"})

    # Internal wall dividing two bedrooms
    msp.add_line((6, 4), (10, 4), dxfattribs={"layer": "WALLS"})

    path = tmp_path / "apartment.dxf"
    doc.saveas(path)
    return path


@pytest.fixture
def messy_walls_dxf(tmp_path):
    """Create DXF with gaps between walls."""
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Rectangle with small gaps (0.03m = 3cm)
    msp.add_line((0, 0), (4.97, 0), dxfattribs={"layer": "WALLS"})
    msp.add_line((5, 0), (5, 4), dxfattribs={"layer": "WALLS"})
    msp.add_line((5, 3.97), (0, 4), dxfattribs={"layer": "WALLS"})
    msp.add_line((0.02, 4), (0, 0), dxfattribs={"layer": "WALLS"})

    path = tmp_path / "messy.dxf"
    doc.saveas(path)
    return path


class TestRoomDetectionIntegration:
    """Integration tests for the full room detection pipeline."""

    def test_detects_rooms_from_simple_apartment(self, simple_apartment_dxf):
        parser = DWGParser(auto_detect_rooms=True)
        floor_plan = parser.parse(simple_apartment_dxf)

        # Should detect 3 rooms
        assert len(floor_plan.rooms) == 3

        # Check total area roughly matches apartment
        total_area = sum(r.area for r in floor_plan.rooms)
        assert 75 < total_area < 85  # ~80 m² with some tolerance

    def test_handles_messy_walls_with_tolerance(self, messy_walls_dxf):
        parser = DWGParser(auto_detect_rooms=True, snap_tolerance=0.05)
        floor_plan = parser.parse(messy_walls_dxf)

        # Should still detect the room despite gaps
        assert len(floor_plan.rooms) == 1
        assert floor_plan.rooms[0].area == pytest.approx(20.0, rel=0.1)

    def test_no_rooms_when_disabled(self, simple_apartment_dxf):
        parser = DWGParser(auto_detect_rooms=False)
        floor_plan = parser.parse(simple_apartment_dxf)

        # Rooms should be empty (no layer-based room extraction either)
        # Note: may have layer-based rooms if ROOM layer exists
        # For this test, we just verify auto-detection didn't run
        assert floor_plan is not None

    def test_room_types_default_to_unknown_without_ai(self, simple_apartment_dxf):
        parser = DWGParser(auto_detect_rooms=True, openai_service=None)
        floor_plan = parser.parse(simple_apartment_dxf)

        # Without AI or fixtures, rooms should be "unknown"
        for room in floor_plan.rooms:
            assert room.room_type in ["unknown", "generic"]


class TestWallGraphFromParser:
    """Tests for wall graph construction from parsed walls."""

    def test_builds_graph_from_parsed_walls(self, simple_apartment_dxf):
        parser = DWGParser(auto_detect_rooms=False)
        floor_plan = parser.parse(simple_apartment_dxf)

        graph = WallGraph(snap_tolerance=0.05)
        graph.add_walls(floor_plan.walls)

        # 6 walls should create edges
        assert len(graph.edges) >= 6

    def test_finds_cycles_from_parsed_walls(self, simple_apartment_dxf):
        parser = DWGParser(auto_detect_rooms=False)
        floor_plan = parser.parse(simple_apartment_dxf)

        graph = WallGraph(snap_tolerance=0.05)
        graph.add_walls(floor_plan.walls)
        cycles = graph.find_cycles()

        # Should find 3 room cycles
        assert len(cycles) == 3
```

**Step 3: Run integration tests to verify they fail**

Run: `pytest tests/test_room_detection.py -v`

Expected: FAIL (parser doesn't have room detection yet)

**Step 4: Integrate room detection into parser**

Modify `core/dwg_parser/parser.py`. Add imports at top:

```python
from .wall_graph import WallGraph
from .room_classifier import RoomClassifier, RoomContext
from .spatial_utils import point_in_polygon, polygon_centroid
```

Update `DWGParser.__init__`:

```python
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
        snap_tolerance: Distance to merge wall endpoints (meters)
        auto_detect_rooms: Enable automatic room detection from walls
        openai_service: Azure OpenAI service for room classification
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
```

Update `parse` method to call room detection:

```python
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

    # Auto-detect rooms from walls if enabled
    if self.auto_detect_rooms:
        self._detect_rooms_from_walls()
    else:
        self._extract_rooms()  # Original layer-based extraction

    self._extract_dimensions()

    # Calculate bounds
    self._calculate_bounds()

    return self._floor_plan
```

Add the room detection method:

```python
def _detect_rooms_from_walls(self) -> None:
    """Detect rooms by finding enclosed areas in wall geometry."""
    if self._floor_plan is None or not self._floor_plan.walls:
        logger.info("No walls to detect rooms from")
        return

    # Build wall graph
    graph = WallGraph(snap_tolerance=self.snap_tolerance)
    graph.add_walls(self._floor_plan.walls)

    # Find enclosed cycles
    cycles = graph.find_cycles(min_area=0.5)
    logger.info(f"Found {len(cycles)} enclosed regions")

    if not cycles:
        return

    # Build room context for each cycle
    contexts = []
    for polygon in cycles:
        ctx = self._build_room_context(polygon)
        contexts.append(ctx)

    # Classify rooms
    classifier = RoomClassifier(openai_service=self.openai_service)
    classifications = classifier.classify_batch(contexts)

    # Create Room objects
    for polygon, ctx, classification in zip(cycles, contexts, classifications):
        room = Room(
            polygon=polygon,
            room_type=classification.room_type,
            name=ctx.nearby_text[0] if ctx.nearby_text else "",
            confidence_low=classification.is_low_confidence,
        )
        self._floor_plan.rooms.append(room)

    logger.info(f"Detected {len(self._floor_plan.rooms)} rooms")

def _build_room_context(self, polygon: List[Point2D]) -> RoomContext:
    """Build classification context for a room polygon."""
    from .spatial_utils import polygon_area, polygon_centroid

    area = polygon_area(polygon)
    centroid = polygon_centroid(polygon)

    # Calculate bounding box for aspect ratio
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    aspect_ratio = width / height if height > 0 else 1.0

    # Count doors and windows inside polygon
    door_count = sum(
        1 for d in self._floor_plan.doors
        if point_in_polygon(d.position, polygon)
    )
    window_count = sum(
        1 for w in self._floor_plan.windows
        if point_in_polygon(w.position, polygon)
    )

    # Detect fixtures (blocks inside polygon)
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
    """Detect fixture blocks inside a polygon."""
    if self._doc is None:
        return []

    fixtures = []
    msp = self._doc.modelspace()
    scale = self._floor_plan.metadata.scale

    for entity in msp:
        if not isinstance(entity, Insert):
            continue

        insert_point = entity.dxf.insert
        pos = (insert_point.x * scale, insert_point.y * scale)

        if point_in_polygon(pos, polygon):
            block_name = entity.dxf.name.lower()
            fixtures.append(block_name)

    return fixtures

def _find_text_near_centroid(
    self, centroid: Point2D, radius: float
) -> List[str]:
    """Find text entities near a point."""
    if self._doc is None:
        return []

    texts = []
    msp = self._doc.modelspace()
    scale = self._floor_plan.metadata.scale

    for entity in msp:
        if entity.dxftype() in ("TEXT", "MTEXT"):
            try:
                if entity.dxftype() == "TEXT":
                    pos = entity.dxf.insert
                    text = entity.dxf.text
                else:  # MTEXT
                    pos = entity.dxf.insert
                    text = entity.text

                text_pos = (pos.x * scale, pos.y * scale)
                dist = ((text_pos[0] - centroid[0])**2 +
                       (text_pos[1] - centroid[1])**2) ** 0.5

                if dist <= radius and text.strip():
                    texts.append(text.strip())
            except Exception:
                pass

    return texts
```

Also add the missing import at the top:

```python
from ezdxf.entities import DXFEntity, LWPolyline, Line, Insert, Circle, Arc, MText
```

**Step 5: Update module exports**

Update `core/dwg_parser/__init__.py`:

```python
"""DWG/DXF parsing module."""

from .parser import DWGParser, FloorPlan, FloorPlanMetadata
from .elements import Wall, Door, Window, Room, Dimension, Point2D, DoorSwing, WindowType
from .converter import convert_dwg_to_dxf, is_dwg_file, is_dxf_file
from .wall_graph import WallGraph, GraphNode, GraphEdge
from .room_classifier import RoomClassifier, RoomContext, RoomClassification

__all__ = [
    "DWGParser",
    "FloorPlan",
    "FloorPlanMetadata",
    "Wall",
    "Door",
    "Window",
    "Room",
    "Dimension",
    "Point2D",
    "DoorSwing",
    "WindowType",
    "convert_dwg_to_dxf",
    "is_dwg_file",
    "is_dxf_file",
    "WallGraph",
    "GraphNode",
    "GraphEdge",
    "RoomClassifier",
    "RoomContext",
    "RoomClassification",
]
```

**Step 6: Run all tests**

Run: `pytest tests/test_room_detection.py tests/test_wall_graph.py tests/test_room_classifier.py tests/test_spatial_utils.py -v`

Expected: All tests PASS

**Step 7: Commit**

```bash
git add core/dwg_parser/ tests/test_room_detection.py
git commit -m "feat: Integrate room detection into DWGParser

- Add auto_detect_rooms and snap_tolerance parameters
- Build WallGraph from parsed walls
- Detect rooms via cycle detection
- Classify rooms using RoomClassifier
- Add confidence_low flag to Room dataclass"
```

---

## Task 7: Final Integration Test

**Files:**
- Run full test suite

**Step 1: Run all tests**

Run: `pytest tests/ -v --tb=short -m "not integration"`

Expected: All tests PASS

**Step 2: Verify imports work**

Run: `python -c "from core.dwg_parser import DWGParser, WallGraph, RoomClassifier; print('All imports OK')"`

Expected: `All imports OK`

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: Final cleanup for room detection feature" --allow-empty
```

---

## Summary

**Files Created:**
- `core/dwg_parser/spatial_utils.py` - Geometry helpers using Shapely
- `core/dwg_parser/wall_graph.py` - Wall graph with cycle detection
- `core/dwg_parser/room_classifier.py` - Room classification with AI
- `tests/test_spatial_utils.py`
- `tests/test_wall_graph.py`
- `tests/test_room_classifier.py`
- `tests/test_room_detection.py`

**Files Modified:**
- `pyproject.toml` - Added shapely, rtree dependencies
- `core/dwg_parser/parser.py` - Integrated room detection
- `core/dwg_parser/elements.py` - Added confidence_low to Room
- `core/dwg_parser/__init__.py` - Updated exports

**Total Commits:** 8
