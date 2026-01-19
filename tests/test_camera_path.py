import pytest
import numpy as np
from core.walkthrough.camera_path import CameraPath, Waypoint


class TestCameraPath:
    """Tests for camera path interpolation."""

    def test_interpolates_between_two_waypoints(self):
        """Should interpolate position between two waypoints."""
        waypoints = [
            Waypoint(position=(0, 1.6, 0), look_at=(0, 1.6, 1), duration=2),
            Waypoint(position=(5, 1.6, 0), look_at=(5, 1.6, 1), duration=2),
        ]

        path = CameraPath(waypoints)

        pos, look = path.get_frame(0)
        assert np.allclose(pos, [0, 1.6, 0], atol=0.01)

        pos, look = path.get_frame(0.5)
        assert np.allclose(pos[0], 2.5, atol=0.5)

        pos, look = path.get_frame(1.0)
        assert np.allclose(pos, [5, 1.6, 0], atol=0.01)

    def test_calculates_total_duration(self):
        """Should sum durations of all waypoints."""
        waypoints = [
            Waypoint(position=(0, 0, 0), look_at=(0, 0, 1), duration=3),
            Waypoint(position=(1, 0, 0), look_at=(1, 0, 1), duration=5),
            Waypoint(position=(2, 0, 0), look_at=(2, 0, 1), duration=2),
        ]

        path = CameraPath(waypoints)

        assert path.total_duration == 10
