"""Video walkthrough generation from camera paths."""

import subprocess
import tempfile
from pathlib import Path

from core.render.blender_renderer import BlenderRenderer, RenderConfig
from core.walkthrough.camera_path import CameraPath, Waypoint


class VideoGenerator:
    """Generates video walkthroughs by rendering frames and encoding."""

    def __init__(
        self,
        fps: int = 30,
        resolution: tuple[int, int] = (1920, 1080),
        blender_renderer: BlenderRenderer | None = None,
    ):
        self.fps = fps
        self.resolution = resolution
        self.renderer = blender_renderer or BlenderRenderer()

    async def generate(
        self,
        gltf_path: str,
        waypoints: list[Waypoint],
        output_path: str,
    ) -> str:
        """Generate a video walkthrough."""
        path = CameraPath(waypoints)
        frame_count = self._calculate_frame_count(path)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            frames = path.get_frames(self.fps)
            for i, (position, look_at) in enumerate(frames):
                frame_path = temp_path / f"frame_{i:05d}.png"
                await self._render_frame(
                    gltf_path=gltf_path,
                    position=tuple(position),
                    look_at=tuple(look_at),
                    output_path=str(frame_path),
                )

            return self._encode_video(temp_path, output_path)

    def _calculate_frame_count(self, path: CameraPath) -> int:
        """Calculate total number of frames needed."""
        return int(path.total_duration * self.fps)

    async def _render_frame(
        self,
        gltf_path: str,
        position: tuple[float, float, float],
        look_at: tuple[float, float, float],
        output_path: str,
    ) -> bytes:
        """Render a single frame using Blender."""
        config = RenderConfig(
            gltf_path=gltf_path,
            output_path=output_path,
            engine="EEVEE",
            resolution=self.resolution,
            camera_position=position,
            camera_look_at=look_at,
        )
        return await self.renderer.render(config)

    def _encode_video(self, frames_dir: Path, output_path: str) -> str:
        """Encode frames to video using FFmpeg."""
        frame_pattern = str(frames_dir / "frame_%05d.png")

        cmd = [
            "ffmpeg",
            "-y",
            "-framerate", str(self.fps),
            "-i", frame_pattern,
            "-c:v", "libx264",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr.decode()}")

        return output_path
