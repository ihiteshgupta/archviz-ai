"""Project management routes."""

import logging
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, field_validator

from core.dwg_parser import DWGParser, FloorPlan

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory project storage (replace with database in production)
PROJECTS: dict = {}
UPLOAD_DIR = Path("uploads")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other security issues.

    - Removes path separators and parent directory references
    - Removes null bytes
    - Limits length
    - Keeps only the basename
    """
    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Get only the basename (removes any path components)
    filename = Path(filename).name

    # Remove any remaining path traversal attempts
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")

    # Remove any control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)

    # Limit length
    if len(filename) > 255:
        # Preserve extension
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:255 - len(ext)] + ext

    # If filename is empty after sanitization, use a default
    if not filename or filename == ".":
        filename = "unknown_file"

    return filename


class ProjectCreate(BaseModel):
    """Project creation request."""

    name: str
    description: Optional[str] = None

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate that name is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError('Project name cannot be empty or whitespace-only')
        # Trim and limit length
        v = v.strip()
        if len(v) > 255:
            v = v[:255]
        return v


class ProjectResponse(BaseModel):
    """Project response."""

    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    status: str
    file_name: Optional[str]
    floor_plan: Optional[dict]


@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Create a new project."""
    project_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    project_data = {
        "id": project_id,
        "name": project.name,
        "description": project.description,
        "created_at": now,
        "updated_at": now,
        "status": "created",
        "file_name": None,
        "floor_plan": None,
    }

    PROJECTS[project_id] = project_data

    # Create project directory
    project_dir = UPLOAD_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Created project: {project_id}")
    return project_data


@router.get("/", response_model=list[ProjectResponse])
async def list_projects():
    """List all projects."""
    return list(PROJECTS.values())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project by ID."""
    if project_id not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")
    return PROJECTS[project_id]


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    if project_id not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete project directory
    project_dir = UPLOAD_DIR / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)

    del PROJECTS[project_id]
    logger.info(f"Deleted project: {project_id}")

    return {"status": "deleted", "id": project_id}


@router.post("/{project_id}/upload")
async def upload_file(project_id: str, file: UploadFile = File(...)):
    """Upload a DWG/DXF file to a project."""
    if project_id not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate file extension
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in [".dwg", ".dxf"]:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only .dwg and .dxf files are supported."
        )

    # Sanitize filename to prevent path traversal
    filename = sanitize_filename(filename)

    # Save uploaded file
    project_dir = UPLOAD_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    file_path = project_dir / filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"Uploaded file: {filename} to project {project_id}")

    # Update project status
    PROJECTS[project_id]["file_name"] = filename
    PROJECTS[project_id]["status"] = "uploaded"
    PROJECTS[project_id]["updated_at"] = datetime.utcnow().isoformat()

    # Parse the floor plan
    try:
        parser = DWGParser()
        floor_plan = parser.parse(file_path)

        PROJECTS[project_id]["floor_plan"] = floor_plan.to_dict()
        PROJECTS[project_id]["status"] = "parsed"

        # Save floor plan JSON
        json_path = project_dir / "floor_plan.json"
        floor_plan.save_json(json_path)

        logger.info(f"Parsed floor plan for project {project_id}")

        return {
            "status": "success",
            "project_id": project_id,
            "file_name": filename,
            "floor_plan": floor_plan.to_dict(),
        }

    except Exception as e:
        logger.error(f"Failed to parse floor plan: {e}")
        PROJECTS[project_id]["status"] = "parse_error"
        raise HTTPException(status_code=500, detail=f"Failed to parse floor plan: {str(e)}")


@router.get("/{project_id}/floor-plan")
async def get_floor_plan(project_id: str):
    """Get parsed floor plan for a project."""
    if project_id not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")

    floor_plan = PROJECTS[project_id].get("floor_plan")
    if not floor_plan:
        raise HTTPException(status_code=404, detail="Floor plan not parsed yet")

    return floor_plan


@router.get("/{project_id}/preview")
async def get_preview(project_id: str):
    """Get SVG preview of floor plan."""
    if project_id not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")

    floor_plan = PROJECTS[project_id].get("floor_plan")
    if not floor_plan:
        raise HTTPException(status_code=404, detail="Floor plan not parsed yet")

    # Generate simple SVG preview
    svg = generate_svg_preview(floor_plan)

    return {"svg": svg, "project_id": project_id}


def generate_svg_preview(floor_plan: dict) -> str:
    """Generate SVG preview from floor plan data."""
    bounds = floor_plan.get("metadata", {}).get("bounds", {})
    min_pt = bounds.get("min", [0, 0])
    max_pt = bounds.get("max", [100, 100])

    width = max_pt[0] - min_pt[0]
    height = max_pt[1] - min_pt[1]

    # Add padding
    padding = max(width, height) * 0.1
    view_min_x = min_pt[0] - padding
    view_min_y = min_pt[1] - padding
    view_width = width + 2 * padding
    view_height = height + 2 * padding

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_min_x} {view_min_y} {view_width} {view_height}">'
    ]

    # Draw walls
    svg_parts.append('<g id="walls" stroke="#333" stroke-width="0.1" fill="none">')
    for wall in floor_plan.get("walls", []):
        points = wall.get("points", [])
        if len(points) >= 2:
            path_data = f"M {points[0][0]} {points[0][1]}"
            for pt in points[1:]:
                path_data += f" L {pt[0]} {pt[1]}"
            svg_parts.append(f'<path d="{path_data}"/>')
    svg_parts.append("</g>")

    # Draw rooms
    svg_parts.append('<g id="rooms" fill="#e3f2fd" fill-opacity="0.5" stroke="#1976d2" stroke-width="0.05">')
    for room in floor_plan.get("rooms", []):
        polygon = room.get("polygon", [])
        if len(polygon) >= 3:
            points_str = " ".join(f"{pt[0]},{pt[1]}" for pt in polygon)
            svg_parts.append(f'<polygon points="{points_str}"/>')
    svg_parts.append("</g>")

    # Draw doors
    svg_parts.append('<g id="doors" fill="#4caf50">')
    for door in floor_plan.get("doors", []):
        pos = door.get("position", [0, 0])
        width = door.get("width", 0.9)
        svg_parts.append(
            f'<rect x="{pos[0] - width/2}" y="{pos[1] - 0.1}" width="{width}" height="0.2"/>'
        )
    svg_parts.append("</g>")

    # Draw windows
    svg_parts.append('<g id="windows" fill="#2196f3">')
    for window in floor_plan.get("windows", []):
        pos = window.get("position", [0, 0])
        width = window.get("width", 1.2)
        svg_parts.append(
            f'<rect x="{pos[0] - width/2}" y="{pos[1] - 0.05}" width="{width}" height="0.1"/>'
        )
    svg_parts.append("</g>")

    svg_parts.append("</svg>")

    return "\n".join(svg_parts)
