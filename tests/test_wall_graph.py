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

        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2

    def test_snap_tolerance_merges_nearby_endpoints(self):
        graph = WallGraph(snap_tolerance=0.1)
        wall1 = Wall(points=[(0, 0), (5, 0)])
        wall2 = Wall(points=[(5.05, 0), (5.05, 5)])
        graph.add_wall(wall1)
        graph.add_wall(wall2)

        assert len(graph.nodes) == 3

    def test_no_merge_beyond_tolerance(self):
        graph = WallGraph(snap_tolerance=0.1)
        wall1 = Wall(points=[(0, 0), (5, 0)])
        wall2 = Wall(points=[(5.2, 0), (5.2, 5)])
        graph.add_wall(wall1)
        graph.add_wall(wall2)

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
        wall2 = Wall(points=[(0, 0), (5, 0)])
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
            graph.add_wall(Wall(points=[points[i], points[i + 1]]))

        cycles = graph.find_cycles()

        assert len(cycles) == 1
        assert len(cycles[0]) == 6

    def test_room_with_internal_wall(self):
        """Room with internal dividing wall should yield two cycles."""
        graph = WallGraph()
        # Outer rectangle 10x4 with walls split at x=5 for internal wall connection
        # Bottom wall split into two segments
        graph.add_wall(Wall(points=[(0, 0), (5, 0)]))
        graph.add_wall(Wall(points=[(5, 0), (10, 0)]))
        # Right wall
        graph.add_wall(Wall(points=[(10, 0), (10, 4)]))
        # Top wall split into two segments
        graph.add_wall(Wall(points=[(10, 4), (5, 4)]))
        graph.add_wall(Wall(points=[(5, 4), (0, 4)]))
        # Left wall
        graph.add_wall(Wall(points=[(0, 4), (0, 0)]))
        # Internal wall dividing at x=5
        graph.add_wall(Wall(points=[(5, 0), (5, 4)]))

        cycles = graph.find_cycles()

        assert len(cycles) == 2

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
