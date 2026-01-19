"""Render pipeline for AI-powered room visualization.

This module provides:
- RoomRenderer: Single room rendering with DALL-E
- BatchRenderer: Multi-room batch orchestration with async support
- PromptBuilder: Constructs DALL-E prompts from room/material data
- JobManager: In-memory job tracking for batch operations

Example usage:
    from core.render import RoomRenderer, BatchRenderer, RenderConfig

    # Single room render
    renderer = RoomRenderer(openai_service, material_library)
    result = await renderer.render_room(room, assignments, RenderConfig(style_preset="modern"))

    # Batch render
    batch = BatchRenderer(openai_service, material_library)
    job_id = await batch.start(floor_plan, assignments, config)

    # Poll for status
    job = batch.get_status(job_id)
    print(f"Progress: {job.completed_rooms}/{job.total_rooms}")
"""

from .batch import BatchRenderer
from .blender_renderer import BlenderRenderer, RenderConfig as BlenderRenderConfig
from .job_manager import JobManager
from .prompt_builder import PromptBuilder
from .renderer import (
    ContentPolicyError,
    RateLimitError,
    RenderException,
    RoomRenderer,
    TimeoutError,
)
from .types import RenderConfig, RenderError, RenderJob, RenderResult

__all__ = [
    # Types
    "RenderConfig",
    "RenderResult",
    "RenderError",
    "RenderJob",
    # Renderers
    "RoomRenderer",
    "BatchRenderer",
    "BlenderRenderer",
    "BlenderRenderConfig",
    # Support classes
    "PromptBuilder",
    "JobManager",
    # Exceptions
    "RenderException",
    "ContentPolicyError",
    "RateLimitError",
    "TimeoutError",
]
