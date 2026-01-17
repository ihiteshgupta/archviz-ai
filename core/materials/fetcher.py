"""External material fetcher for ambientCG integration."""

import asyncio
import io
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from .types import Material


class MaterialFetcher:
    """Fetches PBR materials from ambientCG (CC0 license)."""

    BASE_URL = "https://ambientcg.com/api/v2/full_json"
    DOWNLOAD_URL = "https://ambientcg.com/get"

    # Map ambientCG categories to our categories
    CATEGORY_MAP = {
        "Wood": "wood",
        "WoodFloor": "wood",
        "Bricks": "brick",
        "Concrete": "concrete",
        "Fabric": "fabric",
        "Ground": "stone",
        "Marble": "stone",
        "Metal": "metal",
        "Plaster": "paint",
        "Tiles": "ceramic",
        "Rock": "stone",
        "Leather": "fabric",
    }

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        resolution: str = "1K",
    ):
        """
        Initialize the material fetcher.

        Args:
            cache_dir: Directory for caching downloaded materials
            resolution: Texture resolution ("1K", "2K", "4K")
        """
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "materials",
                "cache",
                "ambientcg",
            )

        self.cache_dir = Path(cache_dir)
        self.resolution = resolution
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search ambientCG for materials.

        Args:
            query: Search query string
            category: Filter by category
            limit: Maximum number of results

        Returns:
            List of asset metadata dictionaries
        """
        session = await self._get_session()

        params = {
            "type": "Material",
            "limit": limit,
            "include": "downloadData,imageData",
        }

        if query:
            params["q"] = query

        if category:
            # Map our category to ambientCG category
            acg_category = None
            for acg_cat, our_cat in self.CATEGORY_MAP.items():
                if our_cat.lower() == category.lower():
                    acg_category = acg_cat
                    break
            if acg_category:
                params["category"] = acg_category

        try:
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                return data.get("foundAssets", [])
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return []

    async def download(self, asset_id: str) -> Optional[Material]:
        """
        Download and cache a material from ambientCG.

        Args:
            asset_id: The ambientCG asset ID

        Returns:
            Material object if successful, None otherwise
        """
        # Check cache first
        if self.is_cached(asset_id):
            return self._load_cached(asset_id)

        session = await self._get_session()

        # Get asset metadata
        params = {
            "type": "Material",
            "id": asset_id,
            "include": "downloadData,imageData",
        }

        try:
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                assets = data.get("foundAssets", [])
                if not assets:
                    return None

                asset = assets[0]

            # Find download URL for requested resolution
            download_url = self._get_download_url(asset)
            if not download_url:
                return None

            # Download ZIP
            async with session.get(download_url) as response:
                if response.status != 200:
                    return None

                zip_data = await response.read()

            # Extract and cache
            material = self._extract_and_cache(asset_id, asset, zip_data)
            return material

        except (aiohttp.ClientError, asyncio.TimeoutError, zipfile.BadZipFile):
            return None

    def _get_download_url(self, asset: Dict[str, Any]) -> Optional[str]:
        """Get the download URL for the requested resolution."""
        downloads = asset.get("downloadFolders", {})

        # Look for PNG downloads at requested resolution
        for folder in downloads.get("default", {}).get("downloadFiletypeCategories", {}).get("zip", {}).get("downloads", []):
            if self.resolution in folder.get("attribute", ""):
                return folder.get("fullDownloadPath")

        # Fall back to any available resolution
        for folder in downloads.get("default", {}).get("downloadFiletypeCategories", {}).get("zip", {}).get("downloads", []):
            return folder.get("fullDownloadPath")

        return None

    def _extract_and_cache(
        self, asset_id: str, asset: Dict[str, Any], zip_data: bytes
    ) -> Material:
        """Extract ZIP and create Material object."""
        cache_path = self.cache_dir / asset_id
        cache_path.mkdir(parents=True, exist_ok=True)

        # Extract ZIP
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            zf.extractall(cache_path)

        # Find texture files
        texture_files = {}
        for file in cache_path.iterdir():
            name_lower = file.name.lower()
            if "color" in name_lower or "diffuse" in name_lower or "albedo" in name_lower:
                texture_files["diffuse"] = str(file)
            elif "normal" in name_lower and "gl" not in name_lower:
                texture_files["normal"] = str(file)
            elif "roughness" in name_lower:
                texture_files["roughness"] = str(file)
            elif "metallic" in name_lower or "metalness" in name_lower:
                texture_files["metallic"] = str(file)
            elif "ao" in name_lower or "ambientocclusion" in name_lower:
                texture_files["ao"] = str(file)

        # Map category
        acg_tags = asset.get("tags", [])
        category = "generic"
        for tag in acg_tags:
            if tag in self.CATEGORY_MAP:
                category = self.CATEGORY_MAP[tag]
                break

        # Create Material
        material = Material(
            id=f"ambientcg_{asset_id.lower()}",
            name=asset.get("name", asset_id),
            category=category,
            base_color=(0.5, 0.5, 0.5),
            roughness=0.5,
            metallic=0.0,
            diffuse_map=texture_files.get("diffuse"),
            normal_map=texture_files.get("normal"),
            roughness_map=texture_files.get("roughness"),
            metallic_map=texture_files.get("metallic"),
            ao_map=texture_files.get("ao"),
            tags=[t.lower() for t in acg_tags[:5]],  # Keep first 5 tags
            suitable_for=["floor", "wall"],  # Default
            room_affinity=[],
            styles=[],
            source="ambientcg",
            source_url=f"https://ambientcg.com/view?id={asset_id}",
        )

        # Save metadata
        self._save_material_metadata(asset_id, material)

        return material

    def _save_material_metadata(self, asset_id: str, material: Material) -> None:
        """Save material metadata to cache."""
        import json

        metadata_path = self.cache_dir / asset_id / "material.json"
        with open(metadata_path, "w") as f:
            json.dump(material.to_dict(), f, indent=2)

    def is_cached(self, asset_id: str) -> bool:
        """Check if a material is cached."""
        cache_path = self.cache_dir / asset_id
        metadata_path = cache_path / "material.json"
        return metadata_path.exists()

    def _load_cached(self, asset_id: str) -> Optional[Material]:
        """Load a cached material."""
        import json

        metadata_path = self.cache_dir / asset_id / "material.json"

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r") as f:
                data = json.load(f)
            return Material.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return None

    def list_cached(self) -> List[str]:
        """List all cached material IDs."""
        if not self.cache_dir.exists():
            return []

        cached = []
        for item in self.cache_dir.iterdir():
            if item.is_dir() and (item / "material.json").exists():
                cached.append(item.name)
        return cached

    def clear_cache(self) -> int:
        """Clear the cache directory. Returns number of items removed."""
        import shutil

        if not self.cache_dir.exists():
            return 0

        count = 0
        for item in self.cache_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                count += 1

        return count
