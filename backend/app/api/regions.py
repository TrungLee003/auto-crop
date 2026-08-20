from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.annotation.models import RegionModel
from app.annotation.service import annotation_service

router = APIRouter(tags=["regions"])


class MergeRegionsRequest(BaseModel):
    region_ids: List[str] = Field(..., min_length=2)


@router.get("/pages/{page_id}/regions", response_model=List[RegionModel])
def get_regions(page_id: str):
    """Get all annotations / regions for a page."""
    try:
        return annotation_service.get_regions(page_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load annotations: {str(e)}"
        )


@router.put("/pages/{page_id}/regions", response_model=List[RegionModel])
def update_regions(page_id: str, regions: List[RegionModel]):
    """Bulk update / replace all annotations for a page (atomic save)."""
    try:
        return annotation_service.update_regions(page_id, regions)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save annotations: {str(e)}"
        )


@router.post("/pages/{page_id}/regions", response_model=RegionModel, status_code=status.HTTP_201_CREATED)
def add_region(page_id: str, region: RegionModel):
    """Add a single region to page."""
    try:
        return annotation_service.add_region(page_id, region)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add region: {str(e)}"
        )


@router.delete("/pages/{page_id}/regions/{region_id}")
def delete_region(page_id: str, region_id: str):
    """Delete a single region."""
    try:
        deleted = annotation_service.delete_region(page_id, region_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")
        return {"status": "ok", "deleted_id": region_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete region: {str(e)}"
        )


@router.post("/pages/{page_id}/regions/{region_id}/fit", response_model=RegionModel)
def fit_region(page_id: str, region_id: str):
    """Tightly fit region bounds around ink illustration content."""
    try:
        return annotation_service.fit_region(page_id, region_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fit region: {str(e)}"
        )


@router.post("/pages/{page_id}/regions/merge", response_model=RegionModel)
def merge_regions(page_id: str, req: MergeRegionsRequest):
    """Merge 2 or more regions into a single polygon region."""
    try:
        return annotation_service.merge_regions(page_id, req.region_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge regions: {str(e)}"
        )
