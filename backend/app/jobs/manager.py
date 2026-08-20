import uuid
from typing import Dict, List, Optional, Union
from .models import JobModel, JobStatus, JobType, TaskStatus, utc_now


class JobManager:
    """
    Centralized manager for background asynchronous jobs and task execution.
    Tracks progress %, current items, errors, timestamps, and cooperative cancellation.
    """
    def __init__(self):
        self._jobs: Dict[str, JobModel] = {}
        self._cancel_flags: Dict[str, bool] = {}

    def create_job(
        self,
        job_type: Union[str, JobType],
        total_items: int = 0,
        message: str = "",
    ) -> JobModel:
        type_str = job_type.value if isinstance(job_type, JobType) else str(job_type)
        job_id = str(uuid.uuid4())[:8]
        job = JobModel(
            id=job_id,
            type=type_str,
            status=JobStatus.RUNNING,
            progress=0.0,
            current_item=0,
            total_items=total_items,
            message=message or f"Starting {type_str}...",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self._jobs[job_id] = job
        self._cancel_flags[job_id] = False
        return job

    def get_job(self, job_id: str) -> Optional[JobModel]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[JobModel]:
        return list(self._jobs.values())

    def update_progress(
        self,
        job_id: Optional[str] = None,
        current_item: int = 0,
        total_items: Optional[int] = None,
        message: Optional[str] = None,
        task_id: Optional[str] = None,
    ):
        target_id = job_id or task_id
        if not target_id:
            return

        job = self._jobs.get(target_id)
        if not job:
            return

        job.current_item = current_item
        if total_items is not None:
            job.total_items = total_items

        if job.total_items > 0:
            job.progress = round((job.current_item / job.total_items) * 100.0, 1)

        if message:
            job.message = message

        job.updated_at = utc_now()

    def complete_job(
        self,
        job_id: Optional[str] = None,
        message: str = "Completed successfully",
        task_id: Optional[str] = None,
    ):
        target_id = job_id or task_id
        if not target_id:
            return

        job = self._jobs.get(target_id)
        if job:
            job.status = JobStatus.DONE
            job.progress = 100.0
            job.message = message
            job.updated_at = utc_now()
            job.completed_at = utc_now()

    def fail_job(
        self,
        job_id: Optional[str] = None,
        error: str = "",
        task_id: Optional[str] = None,
    ):
        target_id = job_id or task_id
        if not target_id:
            return

        job = self._jobs.get(target_id)
        if job:
            job.status = JobStatus.FAILED
            job.error = error
            job.message = f"Failed: {error}"
            job.updated_at = utc_now()
            job.completed_at = utc_now()

    def cancel_job(
        self,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ):
        target_id = job_id or task_id
        if not target_id:
            return

        self._cancel_flags[target_id] = True
        job = self._jobs.get(target_id)
        if job:
            job.status = JobStatus.CANCELLED
            job.message = "Cancelled by user"
            job.updated_at = utc_now()
            job.completed_at = utc_now()

    def is_cancelled(
        self,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> bool:
        target_id = job_id or task_id
        return self._cancel_flags.get(target_id, False) if target_id else False

    # -------------------------------------------------------------------------
    # Backward Compatibility Adapter for TaskManager API
    # -------------------------------------------------------------------------
    def create_task(self, task_type: str, total_items: int = 0, message: str = "") -> TaskStatus:
        job = self.create_job(job_type=task_type, total_items=total_items, message=message)
        return self._to_task_status(job)

    def get_task(self, task_id: str) -> Optional[TaskStatus]:
        job = self.get_job(task_id)
        return self._to_task_status(job) if job else None

    def complete_task(self, task_id: str, message: str = "Completed successfully"):
        self.complete_job(job_id=task_id, message=message)

    def fail_task(self, task_id: str, error: str):
        self.fail_job(job_id=task_id, error=error)

    def cancel_task(self, task_id: str):
        self.cancel_job(job_id=task_id)

    @staticmethod
    def _to_task_status(job: JobModel) -> TaskStatus:
        status_map = {
            JobStatus.QUEUED: "running",
            JobStatus.RUNNING: "running",
            JobStatus.DONE: "completed",
            JobStatus.FAILED: "failed",
            JobStatus.CANCELLED: "cancelled",
        }
        return TaskStatus(
            task_id=job.id,
            task_type=job.type,
            status=status_map.get(job.status, "running"),
            progress=job.progress,
            current_item=job.current_item,
            total_items=job.total_items,
            message=job.message,
            error=job.error,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )


# Global singleton instance
job_manager = JobManager()

