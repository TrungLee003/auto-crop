from app.jobs.models import TaskStatus
from app.jobs.manager import job_manager, JobManager

TaskManager = JobManager
task_manager = job_manager

__all__ = ["TaskStatus", "TaskManager", "task_manager"]
