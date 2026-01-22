"""Render routes for AI-powered architectural visualization."""

import logging
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

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

    @field_validator('resolution')
    @classmethod
    def resolution_must_be_positive(cls, v: int) -> int:
        """Validate that resolution is positive."""
        if v <= 0:
            raise ValueError('Resolution must be a positive integer')
        if v > 4096:
            raise ValueError('Resolution cannot exceed 4096')
        return v


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

VALID_RENDER_SIZES = {"1024x1024", "1792x1024", "1024x1792"}


class QuickRenderRequest(BaseModel):
    """Quick render request using DALL-E 3."""

    room_type: str  # e.g., "living room", "kitchen", "bedroom"
    style: str  # e.g., "modern minimalist", "scandinavian"
    materials: Optional[dict] = None  # Optional material specifications
    additional_details: Optional[str] = None  # Extra description
    size: str = "1024x1024"  # "1024x1024", "1792x1024", "1024x1792"

    @field_validator('size')
    @classmethod
    def size_must_be_valid(cls, v: str) -> str:
        """Validate that size is one of the allowed values."""
        if v not in VALID_RENDER_SIZES:
            raise ValueError(f'Size must be one of: {", ".join(sorted(VALID_RENDER_SIZES))}')
        return v


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


# =============================================================================
# Render Pipeline Integration (core.render)
# =============================================================================

from core.render import (
    BatchRenderer,
    JobManager,
    RenderConfig,
    RoomRenderer,
)
from core.materials.library import MaterialLibrary
from core.materials.types import MaterialAssignment
from core.dwg_parser.elements import Room
from core.dwg_parser.parser import FloorPlan, FloorPlanMetadata

# Shared instances for render pipeline
_job_manager = JobManager()
_batch_renderer = None
_room_renderer = None
_material_library = None


def get_material_library():
    """Get or create material library."""
    global _material_library
    if _material_library is None:
        _material_library = MaterialLibrary()
    return _material_library


def get_room_renderer():
    """Get or create room renderer."""
    global _room_renderer
    if _room_renderer is None:
        dalle_service = get_dalle_service()
        if dalle_service:
            _room_renderer = RoomRenderer(dalle_service, get_material_library())
    return _room_renderer


def get_batch_renderer():
    """Get or create batch renderer."""
    global _batch_renderer
    if _batch_renderer is None:
        dalle_service = get_dalle_service()
        if dalle_service:
            _batch_renderer = BatchRenderer(
                dalle_service,
                get_material_library(),
                max_concurrent=3,
                job_manager=_job_manager,
            )
    return _batch_renderer


# Request/Response Models for Pipeline

class RoomRenderRequest(BaseModel):
    """Request for single room render."""

    room_id: str
    room_name: str
    room_type: str = "generic"
    area: float = 20.0  # square meters
    polygon: list[list[float]] = []  # Room polygon coordinates

    # Material assignments
    floor_material_id: Optional[str] = None
    wall_material_id: Optional[str] = None
    ceiling_material_id: Optional[str] = None

    # Render config
    size: str = "1024x1024"
    quality: str = "hd"
    style_preset: str = "modern"
    lighting: str = "natural"
    time_of_day: str = "day"
    additional_prompt: str = ""


class BatchRenderRequest(BaseModel):
    """Request for batch render of multiple rooms."""

    floor_plan_id: str
    rooms: list[dict]  # List of room data
    material_assignments: list[dict] = []  # Material assignments

    # Render config (applies to all rooms)
    size: str = "1024x1024"
    quality: str = "hd"
    style_preset: str = "modern"
    lighting: str = "natural"
    time_of_day: str = "day"
    additional_prompt: str = ""

    # Optional: specific room IDs to render (all if empty)
    room_ids: list[str] = []


class RenderResultResponse(BaseModel):
    """Response for a single render result."""

    room_id: str
    room_name: str
    image_url: str
    revised_prompt: str
    created_at: str


class BatchJobResponse(BaseModel):
    """Response for batch job status."""

    id: str
    status: str
    floor_plan_id: str
    total_rooms: int
    completed_rooms: int
    progress: float
    successful_renders: int
    failed_renders: int
    results: list[dict]
    errors: list[dict]
    created_at: str
    completed_at: Optional[str]


@router.post("/room", response_model=RenderResultResponse)
async def render_single_room(request: RoomRenderRequest):
    """Render a single room with materials.

    This endpoint renders one room using the render pipeline with
    material assignments and render configuration.
    """
    renderer = get_room_renderer()

    if not renderer:
        raise HTTPException(
            status_code=503,
            detail="Room render requires Azure OpenAI with DALL-E 3. "
                   "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.",
        )

    # Convert polygon to list of tuples
    polygon = [(p[0], p[1]) for p in request.polygon] if request.polygon else []

    # Create Room object
    room = Room(
        id=request.room_id,
        name=request.room_name,
        room_type=request.room_type,
        polygon=polygon or [(0, 0), (5, 0), (5, 4), (0, 4)],  # Default if not provided
    )

    # Create material assignments
    assignments = []
    if request.floor_material_id:
        assignments.append(MaterialAssignment(
            surface_id=f"{request.room_id}_floor",
            material_id=request.floor_material_id,
            room_id=request.room_id,
            surface_type="floor",
        ))
    if request.wall_material_id:
        assignments.append(MaterialAssignment(
            surface_id=f"{request.room_id}_wall",
            material_id=request.wall_material_id,
            room_id=request.room_id,
            surface_type="wall",
        ))
    if request.ceiling_material_id:
        assignments.append(MaterialAssignment(
            surface_id=f"{request.room_id}_ceiling",
            material_id=request.ceiling_material_id,
            room_id=request.room_id,
            surface_type="ceiling",
        ))

    # Create render config
    config = RenderConfig(
        size=request.size,
        quality=request.quality,
        style_preset=request.style_preset,
        lighting=request.lighting,
        time_of_day=request.time_of_day,
        additional_prompt=request.additional_prompt,
    )

    try:
        result = await renderer.render_room(room, assignments, config)

        return RenderResultResponse(
            room_id=result.room_id,
            room_name=result.room_name,
            image_url=result.image_url,
            revised_prompt=result.revised_prompt,
            created_at=result.created_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Room render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchJobResponse)
async def start_batch_render(request: BatchRenderRequest):
    """Start a batch render job for multiple rooms.

    This endpoint queues a batch render job that processes
    multiple rooms asynchronously with concurrency control.
    """
    batch = get_batch_renderer()

    if not batch:
        raise HTTPException(
            status_code=503,
            detail="Batch render requires Azure OpenAI with DALL-E 3. "
                   "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.",
        )

    # Convert room data to Room objects
    rooms = []
    for r in request.rooms:
        polygon = [(p[0], p[1]) for p in r.get("polygon", [])]
        rooms.append(Room(
            id=r.get("id", str(uuid.uuid4())[:8]),
            name=r.get("name", ""),
            room_type=r.get("room_type", "generic"),
            polygon=polygon or [(0, 0), (5, 0), (5, 4), (0, 4)],
        ))

    # Create floor plan
    floor_plan = FloorPlan(
        metadata=FloorPlanMetadata(filename=request.floor_plan_id),
        rooms=rooms,
    )

    # Convert material assignments
    assignments = [
        MaterialAssignment(
            surface_id=a.get("surface_id", ""),
            material_id=a.get("material_id", ""),
            room_id=a.get("room_id"),
            surface_type=a.get("surface_type", "generic"),
        )
        for a in request.material_assignments
    ]

    # Create render config
    config = RenderConfig(
        size=request.size,
        quality=request.quality,
        style_preset=request.style_preset,
        lighting=request.lighting,
        time_of_day=request.time_of_day,
        additional_prompt=request.additional_prompt,
    )

    try:
        # Start batch job
        job_id = await batch.start(
            floor_plan,
            assignments,
            config,
            room_ids=request.room_ids if request.room_ids else None,
        )

        # Return initial status
        job = batch.get_status(job_id)
        return _job_to_response(job)

    except Exception as e:
        logger.error(f"Batch render failed to start: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/{job_id}", response_model=BatchJobResponse)
async def get_batch_job_status(job_id: str):
    """Get the status of a batch render job."""
    job = _job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")

    return _job_to_response(job)


@router.post("/batch/{job_id}/cancel")
async def cancel_batch_job(job_id: str):
    """Cancel a running batch render job."""
    batch = get_batch_renderer()

    if not batch:
        # Try to cancel via job manager directly
        if _job_manager.cancel_job(job_id):
            return {"status": "cancelled", "id": job_id}
        raise HTTPException(status_code=404, detail="Batch job not found")

    if batch.cancel(job_id):
        return {"status": "cancelled", "id": job_id}

    job = _job_manager.get_job(job_id)
    if job and job.is_complete:
        raise HTTPException(status_code=400, detail="Job already completed")

    raise HTTPException(status_code=404, detail="Batch job not found")


@router.get("/batch/jobs/list")
async def list_batch_jobs(
    floor_plan_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
):
    """List batch render jobs with optional filtering."""
    jobs = _job_manager.list_jobs(floor_plan_id=floor_plan_id, status=status)

    # Apply limit
    jobs = jobs[:limit]

    return {
        "jobs": [_job_to_response(job) for job in jobs],
        "total": len(jobs),
    }


@router.delete("/batch/{job_id}")
async def delete_batch_job(job_id: str):
    """Delete a batch render job (must be completed or cancelled)."""
    job = _job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")

    if not job.is_complete:
        raise HTTPException(
            status_code=400,
            detail="Can only delete completed, failed, or cancelled jobs"
        )

    _job_manager.delete_job(job_id)
    return {"status": "deleted", "id": job_id}


@router.get("/pipeline/status")
async def get_pipeline_status():
    """Check render pipeline availability and status."""
    dalle_service = get_dalle_service()
    library = get_material_library()

    active_jobs = _job_manager.list_active_jobs()

    return {
        "available": dalle_service is not None,
        "provider": "azure_openai_dalle3" if dalle_service else None,
        "materials_loaded": library.count() if library else 0,
        "active_jobs": len(active_jobs),
        "pending_jobs": len(_job_manager.list_pending_jobs()),
    }


def _job_to_response(job) -> BatchJobResponse:
    """Convert RenderJob to BatchJobResponse."""
    return BatchJobResponse(
        id=job.id,
        status=job.status,
        floor_plan_id=job.floor_plan_id,
        total_rooms=job.total_rooms,
        completed_rooms=job.completed_rooms,
        progress=round(job.progress, 1),
        successful_renders=job.successful_renders,
        failed_renders=job.failed_renders,
        results=[r.to_dict() for r in job.results],
        errors=[e.to_dict() for e in job.errors],
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )
