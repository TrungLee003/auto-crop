from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobType(str, Enum):
    IMPORT = "IMPORT"
    MASTER_BUILD = "MASTER_BUILD"
    THUMBNAIL = "THUMBNAIL"
    DEEPZOOM = "DEEPZOOM"
    DETECTION = "DETECTION"
    EXPORT_RASTER = "EXPORT_RASTER"
    VECTORIZE = "VECTORIZE"
    BATCH_DETECT = "BATCH_DETECT"
    EXPORT = "EXPORT"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobModel(BaseModel):
    id: str
    type: str
    status: JobStatus = JobStatus.RUNNING
    progress: float = 0.0  # 0 to 100
    current_item: int = 0
    total_items: int = 0
    message: str = ""
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None


class TaskStatus(BaseModel):
    task_id: str
    task_type: str
    status: str = "running"  # "running" | "completed" | "failed" | "cancelled"
    progress: float = 0.0  # 0 to 100
    current_item: int = 0
    total_items: int = 0
    message: str = ""
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
