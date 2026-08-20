from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.annotation.service import annotation_service
from app.export.vector import (
    BUILTIN_PRESETS,
    VTracerPreset,
    generate_vector_preview,
)
from app.project.service import project_service

router = APIRouter(tags=["vector"])


class VectorPreviewRequest(BaseModel):
    preset_id: str = "historical_bw"
    custom_params: Optional[Dict[str, Any]] = None


def _find_page_and_project(page_id: str):
    """Helper to locate a page and its owning project across active projects."""
    for proj in project_service._projects_by_id.values():
        for page in proj.pages:
            if page.id == page_id:
                return page, proj
    return None, None


@router.get("/vector/presets", response_model=List[VTracerPreset])
def list_vector_presets():
    """List all built-in vectorization presets."""
    return list(BUILTIN_PRESETS.values())


@router.post("/pages/{page_id}/regions/{region_id}/vector-preview")
def preview_vector_region(
    page_id: str,
    region_id: str,
    req: Optional[VectorPreviewRequest] = None
):
    """Generate live vector SVG preview for a region."""
    try:
        page, project = _find_page_and_project(page_id)
        if not page or not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Page {page_id} not found")

        master_path = Path(project.root_path) / page.master_path
        if not master_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master image not found on disk")

        regions = annotation_service.get_regions(page_id)
        region = next((r for r in regions if r.id == region_id), None)
        if not region:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Region {region_id} not found")

        request_data = req or VectorPreviewRequest()
        result = generate_vector_preview(
            master_path=master_path,
            region=region,
            preset_id=request_data.preset_id,
            custom_params=request_data.custom_params,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector preview failed: {str(e)}"
        )
