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
