"""Wall graph for detecting enclosed rooms.

Builds a planar graph from wall segments where nodes are endpoints
and edges are wall segments. Uses R-tree for efficient spatial queries.
"""

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from rtree import index

from .elements import Wall, Point2D
from .spatial_utils import distance


@dataclass
class GraphNode:
    """A node in the wall graph representing a wall endpoint."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    position: Point2D = (0.0, 0.0)
    edge_ids: List[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class GraphEdge:
    """An edge in the wall graph representing a wall segment."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_ids: Tuple[str, str] = ("", "")
    wall_id: str = ""

    def __hash__(self) -> int:
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
        self._edge_set: Set[Tuple[str, str]] = set()

        self._spatial_index = index.Index()
        self._node_count = 0

    def add_wall(self, wall: Wall) -> None:
        """Add a wall to the graph."""
        if len(wall.points) < 2:
            return

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
        node_a = self._get_or_create_node(start)
        node_b = self._get_or_create_node(end)

        if node_a.id == node_b.id:
            return

        ids = sorted([node_a.id, node_b.id])
        edge_key: Tuple[str, str] = (ids[0], ids[1])
        if edge_key in self._edge_set:
            return

        edge = GraphEdge(
            node_ids=(node_a.id, node_b.id),
            wall_id=wall_id,
        )
        self.edges[edge.id] = edge
        self._edge_set.add(edge_key)

        node_a.edge_ids.append(edge.id)
        node_b.edge_ids.append(edge.id)

    def _get_or_create_node(self, position: Point2D) -> GraphNode:
        """Get existing node near position or create new one."""
        existing = self.find_node_near(position)
        if existing is not None:
            return existing

        node = GraphNode(position=position)
        self.nodes[node.id] = node

        x, y = position
        self._spatial_index.insert(
            self._node_count,
            (x, y, x, y),
            obj=node.id
        )
        self._node_count += 1

        return node

    def find_node_near(
        self, position: Point2D, tolerance: Optional[float] = None
    ) -> Optional[GraphNode]:
        """Find a node within tolerance of the given position."""
        if tolerance is None:
            tolerance = self.snap_tolerance

        x, y = position
        candidates = list(self._spatial_index.intersection(
            (x - tolerance, y - tolerance, x + tolerance, y + tolerance),
            objects=True
        ))

        best_node = None
        best_dist = float('inf')

        for item in candidates:
            node_id = item.object
            if node_id is None:
                continue
            node = self.nodes.get(node_id)
            if node is None:
                continue
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
