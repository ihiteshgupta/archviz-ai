"""Blender rendering service for high-quality room renders."""

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RenderConfig:
    """Configuration for a render job."""
    gltf_path: str
    output_path: str = ""
    engine: str = "EEVEE"  # EEVEE or CYCLES
    resolution: tuple[int, int] = (1920, 1080)
    samples: int = 64  # For Cycles
    camera_position: tuple[float, float, float] = (5, 2, 5)
    camera_look_at: tuple[float, float, float] = (0, 1, 0)
    hdri_path: str | None = None


class BlenderRenderer:
    """Renders rooms using Blender in headless mode."""

    def __init__(self, blender_path: str = "blender"):
        self.blender_path = blender_path

    async def render(self, config: RenderConfig) -> bytes:
        """Render a room and return the image bytes."""
        script = self._generate_script(config)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            result = subprocess.run(
                [
                    self.blender_path,
                    "--background",
                    "--python", script_path,
                ],
                capture_output=True,
                timeout=300,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Blender failed: {result.stderr.decode()}")

            return Path(config.output_path).read_bytes()
        finally:
            Path(script_path).unlink(missing_ok=True)

    def _generate_script(self, config: RenderConfig) -> str:
        """Generate Blender Python script for rendering."""
        return f'''
import bpy
import mathutils

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath="{config.gltf_path}")

bpy.context.scene.render.engine = "BLENDER_{config.engine}"
bpy.context.scene.render.resolution_x = {config.resolution[0]}
bpy.context.scene.render.resolution_y = {config.resolution[1]}

if "{config.engine}" == "CYCLES":
    bpy.context.scene.cycles.samples = {config.samples}
    bpy.context.scene.cycles.use_denoising = True

bpy.ops.object.camera_add(location={config.camera_position})
camera = bpy.context.active_object
bpy.context.scene.camera = camera

direction = mathutils.Vector({config.camera_look_at}) - mathutils.Vector({config.camera_position})
rot_quat = direction.to_track_quat('-Z', 'Y')
camera.rotation_euler = rot_quat.to_euler()

bpy.ops.object.light_add(type='SUN', location=(10, 10, 10))
sun = bpy.context.active_object
sun.data.energy = 3

bpy.context.scene.world = bpy.data.worlds.new("World")
bpy.context.scene.world.use_nodes = True
bg = bpy.context.scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.8, 0.8, 0.85, 1.0)
bg.inputs[1].default_value = 0.5

bpy.context.scene.render.filepath = "{config.output_path}"
bpy.context.scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print("Render complete: {config.output_path}")
'''
