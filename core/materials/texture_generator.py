# core/materials/texture_generator.py
"""AI-powered texture generation using DALL-E 3."""

import hashlib
import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from core.azure.openai_service import AzureOpenAIService
from core.azure.config import AzureConfig

logger = logging.getLogger(__name__)


TEXTURE_PROMPT = """Seamless tileable texture for {material_name},
top-down orthographic view, flat even lighting, no shadows or highlights,
PBR material reference photograph, {style} interior design style,
high resolution, uniform pattern that tiles perfectly"""


class TextureGenerator:
    """Generates tileable textures using DALL-E 3."""

    def __init__(
        self,
        openai_service: Optional[AzureOpenAIService] = None,
        cache_dir: Optional[str] = None
    ):
        """Initialize texture generator.

        Args:
            openai_service: Azure OpenAI service instance. If None, creates one from env.
            cache_dir: Directory to cache generated textures. Defaults to 'cache/textures'.
        """
        self._openai_service = openai_service
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/textures")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def openai_service(self) -> AzureOpenAIService:
        """Lazy-load OpenAI service from environment if not provided."""
        if self._openai_service is None:
            config = AzureConfig.from_env()
            self._openai_service = AzureOpenAIService(config)
        return self._openai_service

    async def generate(
        self,
        material_name: str,
        style: str = "modern",
        size: int = 512,
    ) -> bytes:
        """Generate a tileable texture for the given material.

        Args:
            material_name: Name/description of the material (e.g., "white oak flooring")
            style: Interior design style (e.g., "modern", "scandinavian")
            size: Output texture size in pixels (square)

        Returns:
            PNG image bytes of the generated texture
        """
        # Check cache first
        cache_key = self._cache_key(material_name, style, size)
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for texture: {material_name}")
            return cached

        logger.info(f"Generating texture for: {material_name} ({style} style)")

        # Generate new texture
        texture_bytes = await self._call_dalle(material_name, style, size)

        # Post-process for better tileability
        processed = self._make_tileable(texture_bytes, size)

        # Cache result
        self._save_cache(cache_key, processed)

        return processed

    async def _call_dalle(
        self,
        material_name: str,
        style: str,
        size: int
    ) -> bytes:
        """Call DALL-E 3 to generate texture.

        Args:
            material_name: Name of the material
            style: Design style
            size: Texture size

        Returns:
            Image bytes from DALL-E
        """
        prompt = TEXTURE_PROMPT.format(
            material_name=material_name,
            style=style
        )

        # DALL-E 3 only supports specific sizes, so we'll generate at closest
        # supported size and resize later
        dalle_size = self._get_dalle_size(size)

        result = await self.openai_service.generate_concept_render(
            prompt=prompt,
            size=dalle_size,
            quality="standard",
        )

        # Fetch the image from URL
        image_url = result.get("url")
        if not image_url:
            raise ValueError("DALL-E did not return an image URL")

        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content

    def _get_dalle_size(self, size: int) -> str:
        """Get the closest DALL-E supported size.

        DALL-E 3 supports: 1024x1024, 1792x1024, 1024x1792
        """
        # For tileable textures, we always want square
        return "1024x1024"

    def _make_tileable(self, image_bytes: bytes, size: int) -> bytes:
        """Post-process image to improve tileability via edge blending.

        Args:
            image_bytes: Raw image bytes
            size: Target output size

        Returns:
            Processed PNG bytes with blended edges
        """
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize to target size
        img = img.resize((size, size), Image.Resampling.LANCZOS)

        # Simple edge blend: average the edges with their opposites
        arr = np.array(img, dtype=np.float32)

        blend_width = size // 8  # 12.5% blend zone

        # Create blend weights
        weights = np.linspace(0, 1, blend_width)

        # Blend left-right edges
        for i, w in enumerate(weights):
            arr[:, i] = arr[:, i] * (1 - w) + arr[:, -(blend_width - i)] * w
            arr[:, -(blend_width - i)] = arr[:, i]

        # Blend top-bottom edges
        for i, w in enumerate(weights):
            arr[i, :] = arr[i, :] * (1 - w) + arr[-(blend_width - i), :] * w
            arr[-(blend_width - i), :] = arr[i, :]

        result = Image.fromarray(arr.astype(np.uint8))

        output = io.BytesIO()
        result.save(output, format="PNG")
        return output.getvalue()

    def _cache_key(self, material: str, style: str, size: int) -> str:
        """Generate cache key for texture.

        Args:
            material: Material name
            style: Style name
            size: Texture size

        Returns:
            MD5 hash of the combined key string
        """
        key_str = f"{material}_{style}_{size}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[bytes]:
        """Get texture from cache if exists.

        Args:
            cache_key: Cache key hash

        Returns:
            Cached texture bytes or None
        """
        cache_path = self.cache_dir / f"{cache_key}.png"
        if cache_path.exists():
            return cache_path.read_bytes()
        return None

    def _save_cache(self, cache_key: str, data: bytes) -> None:
        """Save texture to cache.

        Args:
            cache_key: Cache key hash
            data: Texture bytes to save
        """
        cache_path = self.cache_dir / f"{cache_key}.png"
        cache_path.write_bytes(data)
        logger.debug(f"Cached texture: {cache_path}")

    def clear_cache(self) -> int:
        """Clear all cached textures.

        Returns:
            Number of textures cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.png"):
            cache_file.unlink()
            count += 1
        logger.info(f"Cleared {count} cached textures")
        return count

    def list_cached(self) -> list[str]:
        """List all cached texture keys.

        Returns:
            List of cache keys
        """
        return [f.stem for f in self.cache_dir.glob("*.png")]
