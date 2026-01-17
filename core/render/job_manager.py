"""Job manager for tracking render jobs in memory."""

import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional

from .types import RenderError, RenderJob, RenderResult

logger = logging.getLogger(__name__)


class JobManager:
    """In-memory job tracking for batch render operations."""

    def __init__(self):
        """Initialize the job manager."""
        self._jobs: Dict[str, RenderJob] = {}
        self._lock = threading.Lock()

    def create_job(self, floor_plan_id: str, total_rooms: int) -> RenderJob:
        """
        Create a new render job.

        Args:
            floor_plan_id: ID of the floor plan being rendered
            total_rooms: Total number of rooms to render

        Returns:
            Newly created RenderJob
        """
        job = RenderJob(
            floor_plan_id=floor_plan_id,
            total_rooms=total_rooms,
            status="pending",
            created_at=datetime.now(),
        )

        with self._lock:
            self._jobs[job.id] = job

        logger.info(f"Created render job {job.id} for {total_rooms} rooms")
        return job

    def get_job(self, job_id: str) -> Optional[RenderJob]:
        """
        Get a job by ID.

        Args:
            job_id: Job ID to look up

        Returns:
            RenderJob if found, None otherwise
        """
        with self._lock:
            return self._jobs.get(job_id)

    def start_job(self, job_id: str) -> bool:
        """
        Mark a job as running.

        Args:
            job_id: Job ID to start

        Returns:
            True if job was started, False if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            if job.status != "pending":
                logger.warning(f"Job {job_id} is not pending, current status: {job.status}")
                return False

            job.status = "running"
            logger.info(f"Started render job {job_id}")
            return True

    def update_progress(
        self,
        job_id: str,
        result: Optional[RenderResult] = None,
        error: Optional[RenderError] = None,
    ) -> bool:
        """
        Update job progress with a result or error.

        Args:
            job_id: Job ID to update
            result: Successful render result (optional)
            error: Error information (optional)

        Returns:
            True if updated, False if job not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            if result:
                job.results.append(result)
                job.completed_rooms += 1
                logger.info(
                    f"Job {job_id}: rendered {job.completed_rooms}/{job.total_rooms} - "
                    f"{result.room_name}"
                )

            if error:
                job.errors.append(error)
                job.completed_rooms += 1
                logger.warning(
                    f"Job {job_id}: error rendering {error.room_name} - {error.message}"
                )

            return True

    def mark_completed(self, job_id: str) -> bool:
        """
        Mark a job as completed.

        Args:
            job_id: Job ID to mark complete

        Returns:
            True if marked complete, False if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            job.status = "completed"
            job.completed_at = datetime.now()
            logger.info(
                f"Completed render job {job_id}: "
                f"{job.successful_renders} successful, {job.failed_renders} failed"
            )
            return True

    def mark_failed(self, job_id: str, error_message: str) -> bool:
        """
        Mark a job as failed.

        Args:
            job_id: Job ID to mark failed
            error_message: Reason for failure

        Returns:
            True if marked failed, False if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            job.status = "failed"
            job.completed_at = datetime.now()
            logger.error(f"Render job {job_id} failed: {error_message}")
            return True

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled, False if not found or already complete
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            if job.is_complete:
                logger.warning(f"Job {job_id} is already complete, cannot cancel")
                return False

            job.status = "cancelled"
            job.completed_at = datetime.now()
            logger.info(f"Cancelled render job {job_id}")
            return True

    def list_jobs(
        self,
        floor_plan_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[RenderJob]:
        """
        List all jobs, optionally filtered.

        Args:
            floor_plan_id: Filter by floor plan ID
            status: Filter by status

        Returns:
            List of matching jobs
        """
        with self._lock:
            jobs = list(self._jobs.values())

        if floor_plan_id:
            jobs = [j for j in jobs if j.floor_plan_id == floor_plan_id]

        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs

    def list_active_jobs(self) -> List[RenderJob]:
        """Get all running jobs."""
        return self.list_jobs(status="running")

    def list_pending_jobs(self) -> List[RenderJob]:
        """Get all pending jobs."""
        return self.list_jobs(status="pending")

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the manager.

        Args:
            job_id: Job ID to delete

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                logger.info(f"Deleted render job {job_id}")
                return True
            return False

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Remove completed jobs older than specified age.

        Args:
            max_age_hours: Maximum age in hours for completed jobs

        Returns:
            Number of jobs removed
        """
        cutoff = datetime.now()
        removed = 0

        with self._lock:
            jobs_to_remove = []
            for job_id, job in self._jobs.items():
                if job.is_complete and job.completed_at:
                    age_hours = (cutoff - job.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        jobs_to_remove.append(job_id)

            for job_id in jobs_to_remove:
                del self._jobs[job_id]
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old render jobs")

        return removed

    def clear_all(self) -> int:
        """
        Clear all jobs (for testing/development).

        Returns:
            Number of jobs cleared
        """
        with self._lock:
            count = len(self._jobs)
            self._jobs.clear()
            return count
