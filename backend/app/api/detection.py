from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
from app.annotation.models import RegionModel
from app.detection.base import DetectionConfig
from app.detection.service import detection_service
from app.detection.task_manager import TaskStatus, task_manager

router = APIRouter(tags=["detection"])


class BatchDetectRequest(BaseModel):
    filter_status: Optional[str] = "NEW"
    config: Optional[DetectionConfig] = None


@router.post("/pages/{page_id}/detect", response_model=List[RegionModel])
def detect_single_page(page_id: str, config: Optional[DetectionConfig] = None):
    """Run auto-detection on a single page."""
    try:
        return detection_service.detect_page(page_id, config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {str(e)}"
        )


@router.post("/pages/{page_id}/approve-all", response_model=List[RegionModel])
def approve_all_page_regions(page_id: str):
    """Approve all regions on a page."""
    try:
        return detection_service.approve_all_page_regions(page_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve regions: {str(e)}"
        )


@router.post("/projects/{project_id}/batch-detect")
def start_batch_detection(
    project_id: str,
    background_tasks: BackgroundTasks,
    req: Optional[BatchDetectRequest] = None
):
    """Start async batch auto-detection on project pages."""
    try:
        filter_status = req.filter_status if req else "NEW"
        config = req.config if req else None
        task, page_ids = detection_service.create_batch_detection_task(project_id, filter_status)

        background_tasks.add_task(
            detection_service.run_batch_detection_job,
            task.task_id,
            project_id,
            page_ids,
            config
        )

        return {"status": "started", "task_id": task.task_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start batch detection: {str(e)}"
        )


@router.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task_status(task_id: str):
    """Get status and progress of an async background task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    """Cancel an ongoing background task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    task_manager.cancel_task(task_id)
    return {"status": "cancelled", "task_id": task_id}
