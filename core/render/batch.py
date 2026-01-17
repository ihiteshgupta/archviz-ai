"""Batch renderer for multi-room orchestration."""

import asyncio
import logging
from typing import Dict, List, Optional, Set

from core.azure.openai_service import AzureOpenAIService
from core.dwg_parser.elements import Room
from core.dwg_parser.parser import FloorPlan
from core.materials.library import MaterialLibrary
from core.materials.types import MaterialAssignment

from .job_manager import JobManager
from .renderer import RoomRenderer
from .types import RenderConfig, RenderJob

logger = logging.getLogger(__name__)


class BatchRenderer:
    """Orchestrates batch rendering of multiple rooms."""

    DEFAULT_MAX_CONCURRENT = 3

    def __init__(
        self,
        openai_service: AzureOpenAIService,
        library: MaterialLibrary,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        job_manager: Optional[JobManager] = None,
    ):
        """
        Initialize the batch renderer.

        Args:
            openai_service: Azure OpenAI service for DALL-E
            library: Material library for building prompts
            max_concurrent: Maximum concurrent renders (default: 3)
            job_manager: Optional job manager instance (creates one if not provided)
        """
        self.openai_service = openai_service
        self.library = library
        self.max_concurrent = max_concurrent
        self.job_manager = job_manager or JobManager()
        self.room_renderer = RoomRenderer(openai_service, library)

        # Track active tasks for cancellation
        self._active_tasks: Dict[str, Set[asyncio.Task]] = {}
        self._cancelled_jobs: Set[str] = set()

    async def start(
        self,
        floor_plan: FloorPlan,
        assignments: List[MaterialAssignment],
        config: RenderConfig,
        room_ids: Optional[List[str]] = None,
    ) -> str:
        """
        Start a batch render job.

        Args:
            floor_plan: Floor plan with rooms to render
            assignments: Material assignments for all rooms
            config: Render configuration
            room_ids: Optional list of specific room IDs to render (all if None)

        Returns:
            Job ID for tracking progress
        """
        # Determine which rooms to render
        rooms_to_render = floor_plan.rooms
        if room_ids:
            rooms_to_render = [r for r in floor_plan.rooms if r.id in room_ids]

        if not rooms_to_render:
            logger.warning("No rooms to render in floor plan")
            # Create a job that's already complete
            job = self.job_manager.create_job(
                floor_plan_id=floor_plan.metadata.filename,
                total_rooms=0,
            )
            self.job_manager.mark_completed(job.id)
            return job.id

        # Create job
        job = self.job_manager.create_job(
            floor_plan_id=floor_plan.metadata.filename,
            total_rooms=len(rooms_to_render),
        )

        logger.info(
            f"Starting batch render job {job.id} for {len(rooms_to_render)} rooms"
        )

        # Start background processing
        asyncio.create_task(
            self._process_batch(job.id, rooms_to_render, assignments, config)
        )

        return job.id

    async def _process_batch(
        self,
        job_id: str,
        rooms: List[Room],
        assignments: List[MaterialAssignment],
        config: RenderConfig,
    ) -> None:
        """Process rooms in background with concurrency control."""
        # Mark job as running
        self.job_manager.start_job(job_id)
        self._active_tasks[job_id] = set()

        try:
            # Use semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def render_with_semaphore(room: Room) -> None:
                # Check if job was cancelled
                if job_id in self._cancelled_jobs:
                    return

                async with semaphore:
                    # Check again after acquiring semaphore
                    if job_id in self._cancelled_jobs:
                        return

                    result, error = await self.room_renderer.render_room_safe(
                        room, assignments, config
                    )

                    if result:
                        self.job_manager.update_progress(job_id, result=result)
                    elif error:
                        self.job_manager.update_progress(job_id, error=error)

            # Create tasks for all rooms
            tasks = []
            for room in rooms:
                task = asyncio.create_task(render_with_semaphore(room))
                tasks.append(task)
                self._active_tasks[job_id].add(task)

            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)

            # Mark job as complete (if not cancelled)
            if job_id not in self._cancelled_jobs:
                self.job_manager.mark_completed(job_id)

        except Exception as e:
            logger.error(f"Batch render job {job_id} failed: {e}")
            self.job_manager.mark_failed(job_id, str(e))

        finally:
            # Cleanup
            if job_id in self._active_tasks:
                del self._active_tasks[job_id]
            self._cancelled_jobs.discard(job_id)

    def get_status(self, job_id: str) -> Optional[RenderJob]:
        """
        Get the status of a render job.

        Args:
            job_id: Job ID to check

        Returns:
            RenderJob if found, None otherwise
        """
        return self.job_manager.get_job(job_id)

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a running render job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancellation was initiated, False if job not found/already complete
        """
        job = self.job_manager.get_job(job_id)
        if job is None:
            return False

        if job.is_complete:
            logger.warning(f"Job {job_id} is already complete, cannot cancel")
            return False

        # Mark as cancelled
        self._cancelled_jobs.add(job_id)

        # Cancel active tasks
        if job_id in self._active_tasks:
            for task in self._active_tasks[job_id]:
                task.cancel()

        # Update job status
        self.job_manager.cancel_job(job_id)

        logger.info(f"Cancelled batch render job {job_id}")
        return True

    def list_jobs(self, floor_plan_id: Optional[str] = None) -> List[RenderJob]:
        """
        List all render jobs.

        Args:
            floor_plan_id: Optional filter by floor plan ID

        Returns:
            List of RenderJob objects
        """
        return self.job_manager.list_jobs(floor_plan_id=floor_plan_id)

    async def render_single(
        self,
        room: Room,
        assignments: List[MaterialAssignment],
        config: RenderConfig,
    ):
        """
        Convenience method to render a single room without creating a job.

        Args:
            room: Room to render
            assignments: Material assignments
            config: Render configuration

        Returns:
            RenderResult
        """
        return await self.room_renderer.render_room(room, assignments, config)
