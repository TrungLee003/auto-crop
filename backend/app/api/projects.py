from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from app.project.models import (
    ImportRequest,
    ImportResult,
    ProjectCreate,
    ProjectOpen,
    ProjectResponse,
    ProjectSchema,
    ProjectUpdateRequest,
)
from app.project.service import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectResponse])
def list_projects():
    """List loaded projects."""
    return project_service.list_projects()


@router.post("", response_model=ProjectSchema, status_code=status.HTTP_201_CREATED)
def create_project(req: ProjectCreate):
    """Create a new project folder and structure."""
    try:
        project = project_service.create_project(name=req.name, root_path=req.path)
        return project
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create project: {str(e)}"
        )


@router.post("/open", response_model=ProjectSchema)
def open_project(req: ProjectOpen):
    """Open an existing project by folder path."""
    try:
        project = project_service.open_project(req.path)
        return project
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to open project: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectSchema)
def get_project(project_id: str):
    """Get project schema and pages by ID."""
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    return project


@router.patch("/{project_id}", response_model=ProjectSchema)
def update_project(project_id: str, req: ProjectUpdateRequest):
    """Update project name or settings."""
    try:
        project = project_service.update_project(
            project_id=project_id,
            name=req.name,
            settings=req.settings
        )
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}")
def delete_project(project_id: str, delete_files: bool = False):
    """Delete / close a project."""
    success = project_service.delete_project(project_id, delete_files=delete_files)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    return {"status": "ok", "deleted_id": project_id, "files_deleted": delete_files}


@router.post("/{project_id}/imports", response_model=ImportResult)
def import_scans(project_id: str, req: ImportRequest):
    """Import scans into project."""
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    try:
        result = project_service.import_scans(
            project_id=project_id,
            file_paths=req.file_paths,
            folder_path=req.folder_path,
            mode=req.mode,
            recursive=req.recursive
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Import failed: {str(e)}"
        )


@router.post("/{project_id}/sort-pages", response_model=ProjectSchema)
def sort_project_pages(project_id: str):
    """Sort pages naturally by filename and re-sequence 1..N."""
    try:
        project = project_service.sort_pages(project_id)
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sort pages: {str(e)}"
        )

