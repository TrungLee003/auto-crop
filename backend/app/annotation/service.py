import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.annotation.models import (
    PageAnnotationsSchema,
    RegionGeometry,
    RegionModel,
    RegionStatus,
)
from app.geometry.snapping import fit_region_to_ink_content
from app.geometry.transforms import merge_geometries
from app.project.models import PageStatus, utc_now
from app.project.service import project_service


class AnnotationService:
    @staticmethod
    def _get_page_and_project(page_id: str):
        for project in project_service._projects_by_id.values():
            for page in project.pages:
                if page.id == page_id:
                    return page, project
        return None, None

    @staticmethod
    def load_annotations(project_root: Path, page_id: str) -> PageAnnotationsSchema:
        """Load annotations for a page from annotations/{page_id}.json."""
        anno_file = project_root / "annotations" / f"{page_id}.json"
        if not anno_file.exists():
            return PageAnnotationsSchema(schema_version=2, page_id=page_id, regions=[])

        try:
            with open(anno_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PageAnnotationsSchema(**data)
        except Exception:
            # Check backup if available
            bak_file = project_root / "annotations" / f"{page_id}.json.bak"
            if bak_file.exists():
                with open(bak_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return PageAnnotationsSchema(**data)
            return PageAnnotationsSchema(schema_version=2, page_id=page_id, regions=[])

    @staticmethod
    def save_annotations(
        project_root: Path,
        page_id: str,
        regions: List[RegionModel]
    ) -> PageAnnotationsSchema:
        """
        Atomic save of annotations:
        1. Write to {page_id}.json.tmp
        2. fsync
        3. Backup existing {page_id}.json to .bak
        4. Rename .tmp to {page_id}.json
        5. Update page.region_count
        """
        anno_dir = project_root / "annotations"
        anno_dir.mkdir(parents=True, exist_ok=True)

        target_file = anno_dir / f"{page_id}.json"
        tmp_file = anno_dir / f"{page_id}.json.tmp"
        bak_file = anno_dir / f"{page_id}.json.bak"

        schema = PageAnnotationsSchema(
            schema_version=2,
            page_id=page_id,
            regions=regions,
            updated_at=utc_now()
        )

        data = schema.model_dump(mode="json")

        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        if target_file.exists():
            shutil.copy2(target_file, bak_file)
            target_file.unlink()

        tmp_file.rename(target_file)

        # Update page region count in project schema
        page, project = AnnotationService._get_page_and_project(page_id)
        if page and project:
            page.region_count = len(regions)
            if page.status == PageStatus.NEW and len(regions) > 0:
                page.status = PageStatus.IN_REVIEW
            project_service.save_project(project)

        return schema

    def get_regions(self, page_id: str) -> List[RegionModel]:
        """Get list of regions for a page."""
        page, project = self._get_page_and_project(page_id)
        if not page or not project:
            raise ValueError(f"Page {page_id} not found")

        schema = self.load_annotations(Path(project.root_path), page_id)
        return schema.regions

    def update_regions(self, page_id: str, regions: List[RegionModel]) -> List[RegionModel]:
        """Bulk update / replace all regions for a page."""
        page, project = self._get_page_and_project(page_id)
        if not page or not project:
            raise ValueError(f"Page {page_id} not found")

        # Assign sequences if missing
        for i, r in enumerate(regions, start=1):
            if not r.sequence:
                r.sequence = i

        schema = self.save_annotations(Path(project.root_path), page_id, regions)
        return schema.regions

    def add_region(self, page_id: str, region: RegionModel) -> RegionModel:
        """Add a single region to page."""
        current_regions = self.get_regions(page_id)
        if not region.id:
            region.id = str(uuid.uuid4())
        region.sequence = len(current_regions) + 1
        current_regions.append(region)
        self.update_regions(page_id, current_regions)
        return region

    def delete_region(self, page_id: str, region_id: str) -> bool:
        """Delete a single region by ID."""
        current_regions = self.get_regions(page_id)
        filtered = [r for r in current_regions if r.id != region_id]
        if len(filtered) == len(current_regions):
            return False

        # Re-index sequences
        for i, r in enumerate(filtered, start=1):
            r.sequence = i

        self.update_regions(page_id, filtered)
        return True

    def fit_region(self, page_id: str, region_id: str) -> RegionModel:
        """Tightly fit region boundaries to ink strokes."""
        page, project = self._get_page_and_project(page_id)
        if not page or not project:
            raise ValueError(f"Page {page_id} not found")

        regions = self.get_regions(page_id)
        target = next((r for r in regions if r.id == region_id), None)
        if not target:
            raise ValueError(f"Region {region_id} not found")

        master_abs = Path(project.root_path) / page.master_path
        fitted_geom = fit_region_to_ink_content(master_abs, target.geometry)
        target.geometry = fitted_geom
        target.status = RegionStatus.EDITED
        target.updated_at = utc_now()

        self.update_regions(page_id, regions)
        return target

    def merge_regions(self, page_id: str, region_ids: List[str]) -> RegionModel:
        """Merge multiple regions into a single polygon region."""
        page, project = self._get_page_and_project(page_id)
        if not page or not project:
            raise ValueError(f"Page {page_id} not found")

        regions = self.get_regions(page_id)
        to_merge = [r for r in regions if r.id in region_ids]
        if len(to_merge) < 2:
            raise ValueError("At least 2 regions are required for merge")

        merged_geom = merge_geometries([r.geometry for r in to_merge])

        # Remove merged components and add new merged region
        remaining = [r for r in regions if r.id not in region_ids]
        new_region = RegionModel(
            id=str(uuid.uuid4())[:8],
            sequence=len(remaining) + 1,
            geometry=merged_geom,
            source="manual",
            status=RegionStatus.EDITED,
            padding=to_merge[0].padding,
            export=to_merge[0].export,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        remaining.append(new_region)

        # Re-sequence
        for i, r in enumerate(remaining, start=1):
            r.sequence = i

        self.update_regions(page_id, remaining)
        return new_region


annotation_service = AnnotationService()
