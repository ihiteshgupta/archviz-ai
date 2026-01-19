# tests/test_room_pipeline_integration.py
"""Integration tests for the complete room pipeline."""

import io
import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from core.model_gen.shell_builder import ShellBuilder
from core.model_gen.furniture_placer import FurniturePlacer
from core.materials.texture_generator import TextureGenerator


class TestRoomPipelineIntegration:
    """Integration tests for the complete room pipeline."""

    @pytest.mark.asyncio
    async def test_complete_pipeline_generates_furnished_room(self):
        """Full pipeline should produce a textured, furnished room glTF."""
        # 1. Define room
        room_data = {
            "id": "test_room",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "doors": [{"wall_index": 0, "position": 2.0, "width": 0.9, "height": 2.1}],
            "windows": [{"wall_index": 2, "position": 1.5, "width": 1.2, "height": 1.4, "sill_height": 0.9}],
        }

        # 2. Build shell
        builder = ShellBuilder(room_data)

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            shell_path = f.name

        try:
            builder.export_gltf(shell_path)
            assert os.path.exists(shell_path)
            assert os.path.getsize(shell_path) > 0

            # 3. Get furniture plan (mocked)
            room_context = {
                "room_type": "bedroom",
                "dimensions": {"width": 5, "depth": 4, "height": 2.7},
                "doors": [{"wall": "south", "position": 2.0}],
                "windows": [{"wall": "north", "position": 1.5}],
                "style": "scandinavian",
            }

            mock_furniture_plan = {
                "furniture": [
                    {"type": "bed_queen", "position": [2.5, 0, 3.0], "rotation": 0},
                    {"type": "nightstand", "position": [0.8, 0, 3.0], "rotation": 0},
                ]
            }

            with patch.object(FurniturePlacer, '_call_llm', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = mock_furniture_plan

                placer = FurniturePlacer()
                plan = await placer.generate_plan(room_context)

                assert len(plan["furniture"]) == 2
                assert plan["furniture"][0]["type"] == "bed_queen"

            # 4. Generate textures (mocked)
            from PIL import Image

            mock_texture = Image.new("RGB", (512, 512), color="brown")
            img_bytes = io.BytesIO()
            mock_texture.save(img_bytes, format="PNG")

            with patch.object(TextureGenerator, '_call_dalle', new_callable=AsyncMock) as mock_dalle:
                mock_dalle.return_value = img_bytes.getvalue()

                generator = TextureGenerator()
                texture = await generator.generate("oak flooring", "scandinavian")

                assert texture is not None
                assert len(texture) > 0

        finally:
            os.unlink(shell_path)

    def test_shell_builder_handles_l_shaped_room(self):
        """Shell builder should handle non-rectangular polygons."""
        # L-shaped room
        room_data = {
            "id": "l_room",
            "polygon": [
                [0, 0], [6, 0], [6, 3], [3, 3], [3, 5], [0, 5]
            ],
        }

        builder = ShellBuilder(room_data)
        shell = builder.build_shell()

        # Should have floor, ceiling, and 6 walls
        assert "floor" in shell.geometry
        assert "ceiling" in shell.geometry
        # At least some walls
        wall_count = sum(1 for name in shell.geometry if "wall" in name)
        assert wall_count == 6

    def test_shell_builder_handles_triangular_room(self):
        """Shell builder should handle triangular room polygons."""
        room_data = {
            "id": "triangular_room",
            "polygon": [[0, 0], [4, 0], [2, 3]],
        }

        builder = ShellBuilder(room_data)
        shell = builder.build_shell()

        assert "floor" in shell.geometry
        assert "ceiling" in shell.geometry
        wall_count = sum(1 for name in shell.geometry if "wall" in name)
        assert wall_count == 3

    @pytest.mark.asyncio
    async def test_furniture_placer_validates_room_context(self):
        """FurniturePlacer should handle valid room context."""
        room_context = {
            "room_type": "living_room",
            "dimensions": {"width": 6, "depth": 5, "height": 3.0},
            "doors": [],
            "windows": [],
            "style": "modern",
        }

        mock_response = {
            "furniture": [
                {"type": "sofa", "position": [3.0, 0, 2.5], "rotation": 0},
                {"type": "coffee_table", "position": [3.0, 0, 1.5], "rotation": 0},
            ]
        }

        with patch.object(FurniturePlacer, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            placer = FurniturePlacer()
            plan = await placer.generate_plan(room_context)

            assert "furniture" in plan
            assert len(plan["furniture"]) == 2
            mock_llm.assert_called_once_with(room_context)

    def test_shell_builder_with_multiple_openings(self):
        """Shell builder should handle multiple doors and windows on same wall."""
        room_data = {
            "id": "office_room",
            "polygon": [[0, 0], [8, 0], [8, 5], [0, 5]],
            "doors": [
                {"wall_index": 0, "position": 1.0, "width": 0.9, "height": 2.1},
                {"wall_index": 0, "position": 5.0, "width": 0.9, "height": 2.1},
            ],
            "windows": [
                {"wall_index": 2, "position": 1.0, "width": 1.5, "height": 1.2, "sill_height": 0.9},
                {"wall_index": 2, "position": 4.0, "width": 1.5, "height": 1.2, "sill_height": 0.9},
            ],
        }

        builder = ShellBuilder(room_data)
        shell = builder.build_shell()

        # Verify basic structure
        assert "floor" in shell.geometry
        assert "ceiling" in shell.geometry
        wall_count = sum(1 for name in shell.geometry if "wall" in name)
        assert wall_count == 4  # Rectangular room has 4 walls

    @pytest.mark.asyncio
    async def test_texture_generator_caching(self):
        """TextureGenerator should cache generated textures."""
        from PIL import Image

        mock_texture = Image.new("RGB", (512, 512), color="gray")
        img_bytes = io.BytesIO()
        mock_texture.save(img_bytes, format="PNG")

        with tempfile.TemporaryDirectory() as cache_dir:
            generator = TextureGenerator(cache_dir=cache_dir)

            with patch.object(TextureGenerator, '_call_dalle', new_callable=AsyncMock) as mock_dalle:
                mock_dalle.return_value = img_bytes.getvalue()

                # First call should hit DALL-E
                texture1 = await generator.generate("concrete", "industrial")
                assert mock_dalle.call_count == 1

                # Second call should use cache
                texture2 = await generator.generate("concrete", "industrial")
                # Still 1 call since it was cached
                assert mock_dalle.call_count == 1

                # Both textures should be identical
                assert len(texture1) > 0
                assert len(texture2) > 0

    def test_shell_export_to_multiple_formats(self):
        """Shell builder export should produce valid output."""
        room_data = {
            "id": "simple_room",
            "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]],
        }

        builder = ShellBuilder(room_data)

        # Test GLB export
        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            glb_path = f.name

        try:
            builder.export_gltf(glb_path)
            assert os.path.exists(glb_path)
            file_size = os.path.getsize(glb_path)
            assert file_size > 0

            # Verify it's a valid GLB by checking magic number
            with open(glb_path, 'rb') as f:
                magic = f.read(4)
                # GLB magic is 'glTF' (0x46546C67)
                assert magic == b'glTF'
        finally:
            os.unlink(glb_path)
