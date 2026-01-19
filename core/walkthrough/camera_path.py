"""Camera path interpolation for video walkthroughs."""

from dataclasses import dataclass
import numpy as np
from scipy.interpolate import CubicSpline


@dataclass
class Waypoint:
    """A waypoint in the camera path."""
    position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    duration: float = 3.0


class CameraPath:
    """Smooth camera path through waypoints using cubic spline interpolation."""

    def __init__(self, waypoints: list[Waypoint]):
        if len(waypoints) < 2:
            raise ValueError("Need at least 2 waypoints")

        self.waypoints = waypoints
        self._build_splines()

    @property
    def total_duration(self) -> float:
        """Total duration of the path in seconds."""
        return sum(w.duration for w in self.waypoints)

    def _build_splines(self) -> None:
        """Build cubic splines for position and look_at interpolation."""
        times = [0.0]
        for wp in self.waypoints[1:]:
            times.append(times[-1] + wp.duration)

        total = times[-1]
        self.times = [t / total for t in times]

        positions = np.array([wp.position for wp in self.waypoints])
        look_ats = np.array([wp.look_at for wp in self.waypoints])

        self.pos_spline = CubicSpline(self.times, positions)
        self.look_spline = CubicSpline(self.times, look_ats)

    def get_frame(self, t: float) -> tuple[np.ndarray, np.ndarray]:
        """Get camera position and look_at at normalized time t."""
        t = np.clip(t, 0, 1)
        return self.pos_spline(t), self.look_spline(t)

    def get_frames(self, fps: int = 30) -> list[tuple[np.ndarray, np.ndarray]]:
        """Get all frames for the entire path at given FPS."""
        total_frames = int(self.total_duration * fps)
        frames = []

        for i in range(total_frames):
            t = i / (total_frames - 1) if total_frames > 1 else 0
            frames.append(self.get_frame(t))

        return frames
