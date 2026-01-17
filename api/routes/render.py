"""Render routes for AI-powered architectural visualization."""

import logging
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory render job storage
RENDER_JOBS: dict = {}
OUTPUT_DIR = Path("output")


class RenderStyle(str, Enum):
    """Available render styles."""

    MODERN_MINIMALIST = "modern_minimalist"
    SCANDINAVIAN = "scandinavian"
    INDUSTRIAL = "industrial"
    TRADITIONAL = "traditional"
    MEDITERRANEAN = "mediterranean"
    JAPANESE_ZEN = "japanese_zen"
    ART_DECO = "art_deco"


class RenderStatus(str, Enum):
    """Render job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RenderRequest(BaseModel):
    """Render request parameters."""

    project_id: str
    style: RenderStyle = RenderStyle.MODERN_MINIMALIST
    views: list[str] = ["default"]  # Camera views to render
    resolution: int = 1024
    upscale: bool = True


class RenderJobResponse(BaseModel):
    """Render job response."""

    id: str
    project_id: str
    style: str
    status: str
    created_at: str
    completed_at: Optional[str]
    renders: list[dict]
    error: Optional[str]


@router.post("/", response_model=RenderJobResponse)
async def create_render_job(request: RenderRequest):
    """Create a new render job."""
    job_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    job = {
        "id": job_id,
        "project_id": request.project_id,
        "style": request.style.value,
        "status": RenderStatus.PENDING.value,
        "created_at": now,
        "completed_at": None,
        "renders": [],
        "error": None,
        "config": {
            "views": request.views,
            "resolution": request.resolution,
            "upscale": request.upscale,
        },
    }

    RENDER_JOBS[job_id] = job

    # Create output directory
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Created render job: {job_id} for project {request.project_id}")

    # In production, this would queue the render job
    # For now, return the pending job
    return job


@router.get("/styles")
async def get_render_styles():
    """Get available render styles."""
    return {
        "styles": [
            {
                "id": style.value,
                "name": style.name.replace("_", " ").title(),
                "description": get_style_description(style),
            }
            for style in RenderStyle
        ]
    }


@router.get("/project/{project_id}")
async def get_project_renders(project_id: str):
    """Get all render jobs for a project."""
    jobs = [job for job in RENDER_JOBS.values() if job["project_id"] == project_id]
    return jobs


@router.get("/{job_id}", response_model=RenderJobResponse)
async def get_render_job(job_id: str):
    """Get render job status."""
    if job_id not in RENDER_JOBS:
        raise HTTPException(status_code=404, detail="Render job not found")
    return RENDER_JOBS[job_id]


@router.post("/{job_id}/cancel")
async def cancel_render_job(job_id: str):
    """Cancel a render job."""
    if job_id not in RENDER_JOBS:
        raise HTTPException(status_code=404, detail="Render job not found")

    job = RENDER_JOBS[job_id]
    if job["status"] in [RenderStatus.COMPLETED.value, RenderStatus.FAILED.value]:
        raise HTTPException(status_code=400, detail="Job already finished")

    job["status"] = "cancelled"
    logger.info(f"Cancelled render job: {job_id}")

    return {"status": "cancelled", "id": job_id}


def get_style_description(style: RenderStyle) -> str:
    """Get description for a render style."""
    descriptions = {
        RenderStyle.MODERN_MINIMALIST: "Clean lines, neutral colors, minimal decoration",
        RenderStyle.SCANDINAVIAN: "Light woods, white walls, cozy textiles",
        RenderStyle.INDUSTRIAL: "Exposed brick, metal accents, raw materials",
        RenderStyle.TRADITIONAL: "Classic furniture, warm colors, elegant details",
        RenderStyle.MEDITERRANEAN: "Terracotta, white stucco, arched doorways",
        RenderStyle.JAPANESE_ZEN: "Natural materials, minimalist, peaceful atmosphere",
        RenderStyle.ART_DECO: "Geometric patterns, bold colors, luxurious materials",
    }
    return descriptions.get(style, "")


# =============================================================================
# Quick Concept Render (DALL-E 3)
# =============================================================================

class QuickRenderRequest(BaseModel):
    """Quick render request using DALL-E 3."""

    room_type: str  # e.g., "living room", "kitchen", "bedroom"
    style: str  # e.g., "modern minimalist", "scandinavian"
    materials: Optional[dict] = None  # Optional material specifications
    additional_details: Optional[str] = None  # Extra description
    size: str = "1024x1024"  # "1024x1024", "1792x1024", "1024x1792"


# Lazy-loaded OpenAI service
_dalle_service = None


def get_dalle_service():
    """Get or create DALL-E service."""
    global _dalle_service
    if _dalle_service is None:
        try:
            from core.azure import AzureConfig, AzureOpenAIService
            config = AzureConfig.from_env()
            if config.is_openai_configured():
                _dalle_service = AzureOpenAIService(config)
        except Exception as e:
            logger.warning(f"Azure OpenAI not available for renders: {e}")
    return _dalle_service


@router.post("/quick")
async def create_quick_render(request: QuickRenderRequest):
    """Generate a quick concept render using DALL-E 3.

    This is faster than the full render pipeline but less controllable.
    Good for early concept visualization.
    """
    dalle_service = get_dalle_service()

    if not dalle_service:
        raise HTTPException(
            status_code=503,
            detail="Quick render requires Azure OpenAI with DALL-E 3. "
                   "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.",
        )

    try:
        if request.materials:
            # Use room render with materials
            result = await dalle_service.generate_room_render(
                room_type=request.room_type,
                style=request.style,
                materials=request.materials,
                additional_details=request.additional_details,
                size=request.size,
            )
        else:
            # Generate concept with just description
            prompt = f"{request.style} style {request.room_type}"
            if request.additional_details:
                prompt += f", {request.additional_details}"

            result = await dalle_service.generate_concept_render(
                prompt=prompt,
                style="photorealistic architectural",
                size=request.size,
                quality="hd",
            )

        return {
            "status": "completed",
            "render": {
                "url": result["url"],
                "revised_prompt": result.get("revised_prompt"),
                "size": result["size"],
            },
            "request": {
                "room_type": request.room_type,
                "style": request.style,
            },
            "source": "dalle3",
        }

    except Exception as e:
        logger.error(f"Quick render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick/status")
async def get_quick_render_status():
    """Check if quick render (DALL-E 3) is available."""
    dalle_service = get_dalle_service()
    return {
        "available": dalle_service is not None,
        "provider": "azure_openai_dalle3" if dalle_service else None,
    }
