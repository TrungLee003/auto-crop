from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.project.models import PageModel, PageStatus, PageViewerInfo
from app.project.service import project_service
from app.tiles.server import TileServer

router = APIRouter(tags=["pages"])


class PageUpdateRequest(BaseModel):
    status: Optional[PageStatus] = None
    warnings: Optional[List[str]] = None


def _find_page_and_project(page_id: str):
    """Helper to locate a page and its owning project across active projects."""
    for proj in project_service._projects_by_id.values():
        for page in proj.pages:
            if page.id == page_id:
                return page, proj
    return None, None


@router.get("/projects/{project_id}/pages", response_model=List[PageModel])
def get_pages(project_id: str, status_filter: Optional[str] = Query(None, alias="status")):
    """Get all pages in a project, optionally filtered by status."""
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    pages = project.pages
    if status_filter and status_filter.upper() != "ALL":
        pages = [p for p in pages if p.status.value == status_filter.upper()]

    return pages


@router.get("/pages/{page_id}", response_model=PageModel)
def get_page(page_id: str):
    """Get details for a single page."""
    page, _ = _find_page_and_project(page_id)
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_id} not found"
        )
    return page


@router.patch("/pages/{page_id}", response_model=PageModel)
def update_page(page_id: str, req: PageUpdateRequest):
    """Update page status or warnings."""
    page, project = _find_page_and_project(page_id)
    if not page or not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_id} not found"
        )

    if req.status is not None:
        page.status = req.status
    if req.warnings is not None:
        page.warnings = req.warnings

    project_service.save_project(project)
    return page


@router.delete("/pages/{page_id}")
def delete_page(page_id: str, delete_files: bool = True):
    """Delete a page from the project and remove its cached assets."""
    page, project = _find_page_and_project(page_id)
    if not page or not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_id} not found"
        )

    success = project_service.delete_page(project.project_id, page_id, delete_files=delete_files)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete page"
        )

    return {"status": "ok", "deleted_page_id": page_id}


@router.get("/pages/{page_id}/viewer", response_model=PageViewerInfo)
def get_page_viewer(page_id: str):
    """Get viewer metadata (DZI URL, master dimensions, DPI) for OpenSeadragon."""
    page, project = _find_page_and_project(page_id)
    if not page or not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_id} not found"
        )

    return PageViewerInfo(
        page_id=page.id,
        project_id=project.project_id,
        filename=page.filename,
        master_width=page.width,
        master_height=page.height,
        dpi=page.dpi,
        dzi_url=f"/api/v2/tiles/{project.project_id}/{page.id}/{page.id}.dzi",
        thumbnail_url=f"/api/v2/pages/{page.id}/thumbnail"
    )


@router.get("/pages/{page_id}/thumbnail")
def get_page_thumbnail(page_id: str):
    """Stream page thumbnail image directly."""
    page, project = _find_page_and_project(page_id)
    if not page or not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_id} not found"
        )

    if not page.thumbnail_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not generated"
        )

    thumb_file = Path(project.root_path) / page.thumbnail_path
    if not thumb_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail file not found on disk"
        )

    return FileResponse(str(thumb_file), media_type="image/jpeg")


@router.get("/tiles/{project_id}/{page_id}/{tile_path:path}")
def get_tile(project_id: str, page_id: str, tile_path: str):
    """Stream DZI descriptor and pyramid tiles to OpenSeadragon."""
    return TileServer.serve_tile(project_id=project_id, page_id=page_id, tile_rel_path=tile_path)
