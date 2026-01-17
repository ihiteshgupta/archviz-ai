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
