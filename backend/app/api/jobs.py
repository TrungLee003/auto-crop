from typing import List
from fastapi import APIRouter, HTTPException, status
from app.jobs.manager import job_manager
from app.jobs.models import JobModel

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=List[JobModel])
def list_jobs():
    """List all tracked jobs."""
    return job_manager.list_jobs()


@router.get("/{id}", response_model=JobModel)
def get_job(id: str):
    """Get job status and progress by ID."""
    job = job_manager.get_job(id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {id} not found"
        )
    return job


@router.post("/{id}/cancel")
def cancel_job(id: str):
    """Cancel a running job."""
    job = job_manager.get_job(id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {id} not found"
        )
    job_manager.cancel_job(id)
    return {"status": "cancelled", "job_id": id}
