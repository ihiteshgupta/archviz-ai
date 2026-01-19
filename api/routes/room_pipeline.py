"""Room pipeline API endpoints for 3D generation workflow."""

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from core.model_gen.shell_builder import ShellBuilder


router = APIRouter(prefix="/api/room-pipeline", tags=["room-pipeline"])


# In-memory job storage (replace with Redis in production)
jobs: dict[str, dict[str, Any]] = {}


class GenerateShellRequest(BaseModel):
    """Request model for shell generation."""

    room_id: str
    room_data: dict[str, Any]


class JobResponse(BaseModel):
    """Response model for job creation."""

    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    """Response model for job status queries."""

    job_id: str
    stage: str
    progress: float
    preview_url: str | None = None
    outputs: dict[str, Any] | None = None


@router.post("/generate-shell", response_model=JobResponse)
async def generate_shell(
    request: GenerateShellRequest,
    background_tasks: BackgroundTasks
) -> JobResponse:
    """
    Generate 3D shell from room data.

    Args:
        request: Room data with polygon, doors, and windows
        background_tasks: FastAPI background tasks handler

    Returns:
        Job response with job_id and initial status
    """
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "stage": "SHELL_BUILDING",
        "progress": 0.0,
        "room_id": request.room_id,
        "room_data": request.room_data,
    }

    background_tasks.add_task(_build_shell, job_id, request.room_data)

    return JobResponse(job_id=job_id, status="SHELL_BUILDING")


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get status of a pipeline job.

    Args:
        job_id: UUID of the job to query

    Returns:
        Job status with stage, progress, and optional outputs

    Raises:
        HTTPException: 404 if job not found
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        stage=job["stage"],
        progress=job["progress"],
        preview_url=job.get("preview_url"),
        outputs=job.get("outputs"),
    )


async def _build_shell(job_id: str, room_data: dict[str, Any]) -> None:
    """
    Background task to build 3D shell.

    Args:
        job_id: UUID of the job
        room_data: Room geometry data with polygon, doors, windows
    """
    try:
        builder = ShellBuilder(room_data)

        jobs[job_id]["progress"] = 0.5

        # Export to temp file (in production, upload to blob storage)
        output_path = f"/tmp/{job_id}_shell.glb"
        builder.export_gltf(output_path)

        jobs[job_id]["stage"] = "READY_FOR_FURNISH"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["outputs"] = {"shell_path": output_path}
    except Exception as e:
        jobs[job_id]["stage"] = "FAILED"
        jobs[job_id]["error"] = str(e)
