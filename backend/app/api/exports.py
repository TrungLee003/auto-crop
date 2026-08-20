from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from app.export.models import ExportJobSummary, ExportRequest
from app.export.service import export_service

router = APIRouter(tags=["exports"])


@router.post("/projects/{project_id}/export")
def start_project_export(
    project_id: str,
    background_tasks: BackgroundTasks,
    req: Optional[ExportRequest] = None
):
    """Start async batch export of approved illustrations in 3 streams."""
    try:
        request_data = req if req else ExportRequest()
        task, export_dir, target_items = export_service.create_export_job(project_id, request_data)

        background_tasks.add_task(
            export_service.run_export_job,
            task.task_id,
            project_id,
            export_dir,
            target_items,
            request_data,
        )

        return {
            "status": "started",
            "task_id": task.task_id,
            "export_dir": str(export_dir),
            "total_regions": len(target_items),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start export: {str(e)}"
        )


@router.get("/projects/{project_id}/exports", response_model=List[ExportJobSummary])
def list_project_exports(project_id: str):
    """List all completed export jobs for a project."""
    try:
        return export_service.list_project_exports(project_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list exports: {str(e)}"
        )
