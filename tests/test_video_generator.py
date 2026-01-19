import pytest
from unittest.mock import AsyncMock, patch
from core.walkthrough.video_generator import VideoGenerator
from core.walkthrough.camera_path import CameraPath, Waypoint


class TestVideoGenerator:
    """Tests for video walkthrough generation."""

    def test_calculates_frame_count_from_duration(self):
        """Should calculate correct frame count based on duration and FPS."""
        waypoints = [
            Waypoint(position=(0, 1.6, 0), look_at=(0, 1.6, 1), duration=3),
            Waypoint(position=(5, 1.6, 0), look_at=(5, 1.6, 1), duration=2),
        ]
        path = CameraPath(waypoints)

        generator = VideoGenerator(fps=30)
        frame_count = generator._calculate_frame_count(path)

        assert frame_count == 150  # 5 seconds at 30fps

    @pytest.mark.asyncio
    async def test_generates_video_from_waypoints(self):
        """Should orchestrate frame rendering and video encoding."""
        waypoints = [
            Waypoint(position=(0, 1.6, 0), look_at=(0, 1.6, 1), duration=1),
            Waypoint(position=(2, 1.6, 0), look_at=(2, 1.6, 1), duration=1),
        ]

        generator = VideoGenerator(fps=10)

        with patch.object(generator, '_render_frame', new_callable=AsyncMock) as mock_render:
            with patch.object(generator, '_encode_video') as mock_encode:
                mock_render.return_value = b"fake_frame"
                mock_encode.return_value = "/tmp/output.mp4"

                result = await generator.generate(
                    gltf_path="/tmp/room.glb",
                    waypoints=waypoints,
                    output_path="/tmp/output.mp4",
                )

                assert mock_render.call_count == 20  # 2 seconds at 10fps
                assert mock_encode.called
