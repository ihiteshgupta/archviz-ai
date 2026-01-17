"""Wall graph for detecting enclosed rooms.

Builds a planar graph from wall segments where nodes are endpoints
and edges are wall segments. Uses R-tree for efficient spatial queries.
"""

import math
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from rtree import index

from .elements import Point2D, Wall
from .spatial_utils import distance, polygon_area


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
        self._spatial_index.insert(self._node_count, (x, y, x, y), obj=node.id)
        self._node_count += 1

        return node

    def find_node_near(
        self, position: Point2D, tolerance: Optional[float] = None
    ) -> Optional[GraphNode]:
        """Find a node within tolerance of the given position."""
        if tolerance is None:
            tolerance = self.snap_tolerance

        x, y = position
        candidates = list(
            self._spatial_index.intersection(
                (x - tolerance, y - tolerance, x + tolerance, y + tolerance), objects=True
            )
        )

        best_node = None
        best_dist = float("inf")

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

    def find_cycles(self, min_area: float = 0.5) -> List[List[Point2D]]:
        """Find all minimal cycles (enclosed rooms) in the graph.

        Uses "always turn right" planar traversal algorithm to find
        minimal cycles representing enclosed room polygons.

        Args:
            min_area: Minimum area in square meters for a valid room

        Returns:
            List of cycles, each cycle is a list of vertex positions
        """
        if len(self.edges) == 0:
            return []

        # Track used directed edges: (edge_id, from_node_id)
        used_directed_edges: Set[Tuple[str, str]] = set()
        cycles: List[List[Point2D]] = []

        # Try to trace a cycle from each edge in each direction
        for edge in self.edges.values():
            for start_node_id in edge.node_ids:
                directed_key = (edge.id, start_node_id)
                if directed_key in used_directed_edges:
                    continue

                cycle = self._trace_cycle(edge, start_node_id, used_directed_edges)
                if cycle is not None:
                    cycles.append(cycle)

        # Filter by minimum area
        filtered_cycles = [c for c in cycles if polygon_area(c) >= min_area]

        # Remove outer boundary if we have multiple cycles
        if len(filtered_cycles) > 1:
            filtered_cycles = self._remove_outer_boundary(filtered_cycles)

        return filtered_cycles

    def _trace_cycle(
        self,
        start_edge: GraphEdge,
        start_from_node_id: str,
        used_directed_edges: Set[Tuple[str, str]],
    ) -> Optional[List[Point2D]]:
        """Trace a cycle starting from a directed edge using rightmost turns.

        Args:
            start_edge: The edge to start from
            start_from_node_id: The node we're coming from
            used_directed_edges: Set of already used directed edges

        Returns:
            List of vertex positions forming the cycle, or None if no cycle found
        """
        cycle_nodes: List[str] = []
        cycle_edges: List[Tuple[str, str]] = []  # (edge_id, from_node_id)

        current_edge = start_edge
        current_from_node_id = start_from_node_id
        current_node = self.get_other_node(current_edge, current_from_node_id)

        if current_node is None:
            return None

        start_node = self.nodes.get(start_from_node_id)
        if start_node is None:
            return None

        # Track the starting point
        target_node_id = start_from_node_id
        max_iterations = len(self.edges) * 2 + 10

        for _ in range(max_iterations):
            # Record this directed edge
            directed_key = (current_edge.id, current_from_node_id)
            if directed_key in used_directed_edges:
                # This directed edge was already used in another cycle
                return None

            cycle_nodes.append(current_node.id)
            cycle_edges.append(directed_key)

            # Check if we've returned to start
            if current_node.id == target_node_id and len(cycle_nodes) >= 3:
                # Found a valid cycle - mark all directed edges as used
                for edge_key in cycle_edges:
                    used_directed_edges.add(edge_key)

                # Convert node ids to positions
                return [self.nodes[nid].position for nid in cycle_nodes]

            # Find the next edge using rightmost turn
            prev_node = self.nodes.get(current_from_node_id)
            if prev_node is None:
                return None

            next_edge = self._find_rightmost_edge(current_node, prev_node, current_edge)
            if next_edge is None:
                return None

            # Move to next edge
            current_from_node_id = current_node.id
            current_edge = next_edge
            next_node = self.get_other_node(current_edge, current_node.id)
            if next_node is None:
                return None
            current_node = next_node

        # Exceeded max iterations - no cycle found
        return None

    def _find_rightmost_edge(
        self,
        current_node: GraphNode,
        prev_node: GraphNode,
        current_edge: GraphEdge,
    ) -> Optional[GraphEdge]:
        """Find the edge representing the rightmost turn from current position.

        Uses angle calculations to determine which outgoing edge represents
        the rightmost (most clockwise) turn from the incoming direction.

        Args:
            current_node: The node we're at
            prev_node: The node we came from
            current_edge: The edge we arrived on

        Returns:
            The edge to take for a rightmost turn, or None if dead end
        """
        edges = self.get_edges_from_node(current_node.id)
        if len(edges) == 0:
            return None

        if len(edges) == 1:
            # Dead end - only edge is the one we came from
            return None

        # Calculate incoming direction angle
        dx_in = current_node.position[0] - prev_node.position[0]
        dy_in = current_node.position[1] - prev_node.position[1]
        incoming_angle = math.atan2(dy_in, dx_in)

        best_edge = None
        best_turn_angle = float("-inf")

        for edge in edges:
            # Skip the edge we came from
            if edge.id == current_edge.id:
                continue

            # Get the other node on this edge
            other_node = self.get_other_node(edge, current_node.id)
            if other_node is None:
                continue

            # Calculate outgoing direction angle
            dx_out = other_node.position[0] - current_node.position[0]
            dy_out = other_node.position[1] - current_node.position[1]
            outgoing_angle = math.atan2(dy_out, dx_out)

            # Calculate turn angle (how much we turn right)
            # Positive = right turn, negative = left turn
            # We want the most negative (rightmost) turn
            turn_angle = outgoing_angle - incoming_angle

            # Normalize to [-pi, pi]
            while turn_angle > math.pi:
                turn_angle -= 2 * math.pi
            while turn_angle < -math.pi:
                turn_angle += 2 * math.pi

            # For rightmost turn, we want the smallest (most negative) angle
            # But we negate here to use max comparison
            right_turn_score = -turn_angle

            if right_turn_score > best_turn_angle:
                best_turn_angle = right_turn_score
                best_edge = edge

        return best_edge

    def _remove_outer_boundary(self, cycles: List[List[Point2D]]) -> List[List[Point2D]]:
        """Remove the outer boundary cycle when there are interior cycles.

        The outer boundary is identified as the cycle with the largest area.

        Args:
            cycles: List of cycles

        Returns:
            Cycles with outer boundary removed
        """
        if len(cycles) <= 1:
            return cycles

        # Find the cycle with the largest area (outer boundary)
        max_area = 0.0
        max_index = -1

        for i, cycle in enumerate(cycles):
            area = polygon_area(cycle)
            if area > max_area:
                max_area = area
                max_index = i

        # Remove the outer boundary
        if max_index >= 0:
            return cycles[:max_index] + cycles[max_index + 1 :]

        return cycles
