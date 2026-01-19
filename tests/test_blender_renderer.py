import pytest
from core.render.blender_renderer import BlenderRenderer, RenderConfig


class TestBlenderRenderer:
    """Tests for Blender rendering service."""

    def test_render_config_defaults(self):
        """RenderConfig should have sensible defaults."""
        config = RenderConfig(gltf_path="/tmp/test.glb")

        assert config.engine == "EEVEE"
        assert config.resolution == (1920, 1080)
        assert config.samples == 64

    def test_generates_render_script(self):
        """Should generate valid Blender Python script."""
        renderer = BlenderRenderer()
        config = RenderConfig(
            gltf_path="/tmp/room.glb",
            output_path="/tmp/render.png",
            camera_position=(5, 2, 5),
            camera_look_at=(0, 1, 0),
        )

        script = renderer._generate_script(config)

        assert "import bpy" in script
        assert "/tmp/room.glb" in script
        assert "/tmp/render.png" in script
        assert "camera" in script.lower()
