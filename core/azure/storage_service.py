"""Azure Blob Storage service for file management."""

import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import BinaryIO, Optional

from azure.storage.blob import (
    BlobServiceClient,
    BlobClient,
    ContainerClient,
    generate_blob_sas,
    BlobSasPermissions,
)

from .config import AzureConfig

logger = logging.getLogger(__name__)


class AzureBlobStorageService:
    """Azure Blob Storage service for file uploads and management."""

    def __init__(self, config: AzureConfig):
        self.config = config
        self._client: Optional[BlobServiceClient] = None

    @property
    def client(self) -> BlobServiceClient:
        """Get or create Blob Storage client."""
        if self._client is None:
            if not self.config.is_storage_configured():
                raise ValueError(
                    "Azure Blob Storage is not configured. "
                    "Set AZURE_STORAGE_CONNECTION_STRING or account name/key."
                )

            if self.config.storage_connection_string:
                self._client = BlobServiceClient.from_connection_string(
                    self.config.storage_connection_string
                )
            else:
                account_url = f"https://{self.config.storage_account_name}.blob.core.windows.net"
                self._client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.config.storage_account_key,
                )

        return self._client

    def get_container(self, container_name: str) -> ContainerClient:
        """Get container client, creating if necessary."""
        container = self.client.get_container_client(container_name)
        if not container.exists():
            container.create_container()
            logger.info(f"Created container: {container_name}")
        return container

    async def upload_file(
        self,
        container_name: str,
        file_data: BinaryIO,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Upload a file to blob storage."""
        try:
            container = self.get_container(container_name)

            # Generate unique blob name
            ext = Path(filename).suffix
            blob_name = f"{uuid.uuid4().hex[:12]}_{filename}"

            blob_client = container.get_blob_client(blob_name)

            # Set content settings
            content_settings = None
            if content_type:
                from azure.storage.blob import ContentSettings
                content_settings = ContentSettings(content_type=content_type)

            # Upload
            blob_client.upload_blob(
                file_data,
                overwrite=True,
                content_settings=content_settings,
                metadata=metadata,
            )

            logger.info(f"Uploaded blob: {blob_name} to {container_name}")

            return {
                "blob_name": blob_name,
                "container": container_name,
                "url": blob_client.url,
                "size": blob_client.get_blob_properties().size,
            }
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise

    async def upload_project_file(
        self,
        project_id: str,
        file_data: BinaryIO,
        filename: str,
    ) -> dict:
        """Upload a project file (DWG/DXF) to the uploads container."""
        # Organize by project
        blob_name = f"projects/{project_id}/{filename}"

        container = self.get_container(self.config.uploads_container)
        blob_client = container.get_blob_client(blob_name)

        # Determine content type
        ext = Path(filename).suffix.lower()
        content_type = {
            ".dwg": "application/acad",
            ".dxf": "application/dxf",
            ".json": "application/json",
        }.get(ext, "application/octet-stream")

        from azure.storage.blob import ContentSettings
        content_settings = ContentSettings(content_type=content_type)

        blob_client.upload_blob(
            file_data,
            overwrite=True,
            content_settings=content_settings,
            metadata={"project_id": project_id, "original_name": filename},
        )

        return {
            "blob_name": blob_name,
            "url": blob_client.url,
            "project_id": project_id,
        }

    async def upload_render(
        self,
        project_id: str,
        job_id: str,
        image_data: bytes,
        view_name: str = "default",
        format: str = "png",
    ) -> dict:
        """Upload a rendered image to the renders container."""
        blob_name = f"projects/{project_id}/renders/{job_id}/{view_name}.{format}"

        container = self.get_container(self.config.renders_container)
        blob_client = container.get_blob_client(blob_name)

        from azure.storage.blob import ContentSettings
        content_type = f"image/{format}"
        content_settings = ContentSettings(content_type=content_type)

        blob_client.upload_blob(
            image_data,
            overwrite=True,
            content_settings=content_settings,
            metadata={
                "project_id": project_id,
                "job_id": job_id,
                "view": view_name,
            },
        )

        # Generate SAS URL for access
        sas_url = self.generate_sas_url(
            self.config.renders_container,
            blob_name,
            expiry_hours=24,
        )

        return {
            "blob_name": blob_name,
            "url": sas_url,
            "view": view_name,
            "format": format,
        }

    async def download_file(
        self,
        container_name: str,
        blob_name: str,
    ) -> bytes:
        """Download a file from blob storage."""
        try:
            container = self.get_container(container_name)
            blob_client = container.get_blob_client(blob_name)

            return blob_client.download_blob().readall()
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise

    async def delete_file(
        self,
        container_name: str,
        blob_name: str,
    ) -> bool:
        """Delete a file from blob storage."""
        try:
            container = self.get_container(container_name)
            blob_client = container.get_blob_client(blob_name)
            blob_client.delete_blob()

            logger.info(f"Deleted blob: {blob_name}")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    async def delete_project_files(self, project_id: str) -> int:
        """Delete all files associated with a project."""
        deleted_count = 0

        for container_name in [
            self.config.uploads_container,
            self.config.renders_container,
            self.config.textures_container,
        ]:
            try:
                container = self.get_container(container_name)
                prefix = f"projects/{project_id}/"

                blobs = container.list_blobs(name_starts_with=prefix)
                for blob in blobs:
                    container.delete_blob(blob.name)
                    deleted_count += 1

            except Exception as e:
                logger.warning(f"Error cleaning {container_name}: {e}")

        logger.info(f"Deleted {deleted_count} files for project {project_id}")
        return deleted_count

    def generate_sas_url(
        self,
        container_name: str,
        blob_name: str,
        expiry_hours: int = 24,
        permissions: str = "r",
    ) -> str:
        """Generate a SAS URL for blob access."""
        if not self.config.storage_account_key:
            # If using connection string, extract key
            raise ValueError("Storage account key required for SAS generation")

        sas_token = generate_blob_sas(
            account_name=self.config.storage_account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=self.config.storage_account_key,
            permission=BlobSasPermissions(read="r" in permissions, write="w" in permissions),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
        )

        return (
            f"https://{self.config.storage_account_name}.blob.core.windows.net/"
            f"{container_name}/{blob_name}?{sas_token}"
        )

    async def list_project_renders(self, project_id: str) -> list[dict]:
        """List all renders for a project."""
        renders = []

        try:
            container = self.get_container(self.config.renders_container)
            prefix = f"projects/{project_id}/renders/"

            blobs = container.list_blobs(name_starts_with=prefix)
            for blob in blobs:
                renders.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created": blob.creation_time,
                    "url": self.generate_sas_url(
                        self.config.renders_container,
                        blob.name,
                    ),
                })

        except Exception as e:
            logger.error(f"Error listing renders: {e}")

        return renders

    async def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""
        stats = {
            "containers": {},
            "total_size": 0,
            "total_blobs": 0,
        }

        for container_name in [
            self.config.uploads_container,
            self.config.renders_container,
            self.config.textures_container,
            self.config.models_container,
        ]:
            try:
                container = self.get_container(container_name)
                size = 0
                count = 0

                for blob in container.list_blobs():
                    size += blob.size or 0
                    count += 1

                stats["containers"][container_name] = {
                    "size_bytes": size,
                    "size_mb": round(size / 1024 / 1024, 2),
                    "blob_count": count,
                }
                stats["total_size"] += size
                stats["total_blobs"] += count

            except Exception as e:
                stats["containers"][container_name] = {"error": str(e)}

        stats["total_size_mb"] = round(stats["total_size"] / 1024 / 1024, 2)
        return stats
