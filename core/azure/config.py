"""Azure configuration management."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AzureConfig:
    """Azure service configuration."""

    # Azure OpenAI
    openai_endpoint: str
    openai_api_key: str
    openai_api_version: str = "2024-02-15-preview"

    # Model deployments
    gpt4_deployment: str = "gpt-4o"
    gpt4_vision_deployment: str = "gpt-4o"
    dalle_deployment: str = "dall-e-3"

    # Azure Blob Storage
    storage_account_name: str = ""
    storage_account_key: str = ""
    storage_connection_string: str = ""

    # Container names
    uploads_container: str = "uploads"
    renders_container: str = "renders"
    textures_container: str = "textures"
    models_container: str = "models"

    # Azure ML (for ControlNet pipeline)
    ml_workspace_name: Optional[str] = None
    ml_endpoint_name: Optional[str] = None
    ml_endpoint_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AzureConfig":
        """Load configuration from environment variables."""
        return cls(
            # OpenAI
            openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            gpt4_deployment=os.getenv("AZURE_OPENAI_GPT4_DEPLOYMENT", "gpt-4o"),
            gpt4_vision_deployment=os.getenv("AZURE_OPENAI_GPT4V_DEPLOYMENT", "gpt-4o"),
            dalle_deployment=os.getenv("AZURE_OPENAI_DALLE_DEPLOYMENT", "dall-e-3"),

            # Storage
            storage_account_name=os.getenv("AZURE_STORAGE_ACCOUNT_NAME", ""),
            storage_account_key=os.getenv("AZURE_STORAGE_ACCOUNT_KEY", ""),
            storage_connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),

            # Containers
            uploads_container=os.getenv("AZURE_UPLOADS_CONTAINER", "uploads"),
            renders_container=os.getenv("AZURE_RENDERS_CONTAINER", "renders"),
            textures_container=os.getenv("AZURE_TEXTURES_CONTAINER", "textures"),
            models_container=os.getenv("AZURE_MODELS_CONTAINER", "models"),

            # ML
            ml_workspace_name=os.getenv("AZURE_ML_WORKSPACE"),
            ml_endpoint_name=os.getenv("AZURE_ML_ENDPOINT"),
            ml_endpoint_key=os.getenv("AZURE_ML_ENDPOINT_KEY"),
        )

    def is_openai_configured(self) -> bool:
        """Check if Azure OpenAI is properly configured."""
        return bool(self.openai_endpoint and self.openai_api_key)

    def is_storage_configured(self) -> bool:
        """Check if Azure Blob Storage is properly configured."""
        return bool(self.storage_connection_string or
                   (self.storage_account_name and self.storage_account_key))

    def is_ml_configured(self) -> bool:
        """Check if Azure ML is configured for pro renders."""
        return bool(self.ml_endpoint_name and self.ml_endpoint_key)
