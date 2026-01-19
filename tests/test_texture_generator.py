# tests/test_texture_generator.py
"""Tests for AI texture generation."""

import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from core.materials.texture_generator import TextureGenerator


class TestTextureGenerator:
    """Tests for AI texture generation."""

    @pytest.mark.asyncio
    async def test_generates_texture_for_material(self):
        """Should generate a texture image for a given material."""
        # Mock DALL-E response with a simple image
        mock_image = Image.new("RGB", (512, 512), color="brown")
        img_bytes = io.BytesIO()
        mock_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        with patch.object(TextureGenerator, '_call_dalle', new_callable=AsyncMock) as mock_dalle:
            mock_dalle.return_value = img_bytes.getvalue()

            with tempfile.TemporaryDirectory() as tmpdir:
                generator = TextureGenerator(cache_dir=tmpdir)
                texture = await generator.generate(
                    material_name="white oak flooring",
                    style="scandinavian"
                )

                assert texture is not None
                assert isinstance(texture, bytes)

                # Verify it's a valid image
                img = Image.open(io.BytesIO(texture))
                assert img.size == (512, 512)

    @pytest.mark.asyncio
    async def test_uses_cache_on_second_call(self):
        """Should return cached texture on subsequent calls."""
        mock_image = Image.new("RGB", (512, 512), color="brown")
        img_bytes = io.BytesIO()
        mock_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        with patch.object(TextureGenerator, '_call_dalle', new_callable=AsyncMock) as mock_dalle:
            mock_dalle.return_value = img_bytes.getvalue()

            with tempfile.TemporaryDirectory() as tmpdir:
                generator = TextureGenerator(cache_dir=tmpdir)

                # First call - should hit DALL-E
                texture1 = await generator.generate(
                    material_name="white oak flooring",
                    style="scandinavian"
                )

                # Second call - should use cache
                texture2 = await generator.generate(
                    material_name="white oak flooring",
                    style="scandinavian"
                )

                # DALL-E should only be called once
                assert mock_dalle.call_count == 1
                assert texture1 == texture2

    @pytest.mark.asyncio
    async def test_different_materials_generate_different_textures(self):
        """Different materials should generate different textures."""
        brown_image = Image.new("RGB", (512, 512), color="brown")
        brown_bytes = io.BytesIO()
        brown_image.save(brown_bytes, format="PNG")
        brown_bytes.seek(0)

        gray_image = Image.new("RGB", (512, 512), color="gray")
        gray_bytes = io.BytesIO()
        gray_image.save(gray_bytes, format="PNG")
        gray_bytes.seek(0)

        with patch.object(TextureGenerator, '_call_dalle', new_callable=AsyncMock) as mock_dalle:
            mock_dalle.side_effect = [brown_bytes.getvalue(), gray_bytes.getvalue()]

            with tempfile.TemporaryDirectory() as tmpdir:
                generator = TextureGenerator(cache_dir=tmpdir)

                texture1 = await generator.generate(
                    material_name="white oak flooring",
                    style="modern"
                )
                texture2 = await generator.generate(
                    material_name="gray concrete",
                    style="industrial"
                )

                assert mock_dalle.call_count == 2
                assert texture1 != texture2

    @pytest.mark.asyncio
    async def test_custom_size(self):
        """Should respect custom size parameter."""
        mock_image = Image.new("RGB", (256, 256), color="brown")
        img_bytes = io.BytesIO()
        mock_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        with patch.object(TextureGenerator, '_call_dalle', new_callable=AsyncMock) as mock_dalle:
            mock_dalle.return_value = img_bytes.getvalue()

            with tempfile.TemporaryDirectory() as tmpdir:
                generator = TextureGenerator(cache_dir=tmpdir)
                texture = await generator.generate(
                    material_name="marble",
                    style="modern",
                    size=256
                )

                img = Image.open(io.BytesIO(texture))
                assert img.size == (256, 256)

    def test_cache_key_generation(self):
        """Cache key should be deterministic for same inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TextureGenerator(cache_dir=tmpdir)

            key1 = generator._cache_key("oak wood", "modern", 512)
            key2 = generator._cache_key("oak wood", "modern", 512)
            key3 = generator._cache_key("oak wood", "scandinavian", 512)

            assert key1 == key2
            assert key1 != key3

    def test_cache_directory_created(self):
        """Cache directory should be created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "textures" / "nested"
            generator = TextureGenerator(cache_dir=str(cache_path))
            assert cache_path.exists()

    @pytest.mark.asyncio
    async def test_make_tileable_creates_valid_image(self):
        """Edge blending should produce a valid image."""
        # Create a test image
        test_image = Image.new("RGB", (512, 512), color="brown")
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TextureGenerator(cache_dir=tmpdir)
            result = generator._make_tileable(img_bytes.getvalue(), 512)

            # Should produce valid PNG bytes
            img = Image.open(io.BytesIO(result))
            assert img.size == (512, 512)
            assert img.mode == "RGB"


class TestTexturePrompt:
    """Tests for texture prompt generation."""

    def test_prompt_includes_material_name(self):
        """Prompt should include the material name."""
        from core.materials.texture_generator import TEXTURE_PROMPT

        formatted = TEXTURE_PROMPT.format(
            material_name="white oak flooring",
            style="scandinavian"
        )
        assert "white oak flooring" in formatted

    def test_prompt_includes_style(self):
        """Prompt should include the style."""
        from core.materials.texture_generator import TEXTURE_PROMPT

        formatted = TEXTURE_PROMPT.format(
            material_name="white oak flooring",
            style="scandinavian"
        )
        assert "scandinavian" in formatted

    def test_prompt_mentions_tileable(self):
        """Prompt should request tileable texture."""
        from core.materials.texture_generator import TEXTURE_PROMPT

        formatted = TEXTURE_PROMPT.format(
            material_name="marble",
            style="modern"
        )
        assert "tileable" in formatted.lower() or "tiles" in formatted.lower()
