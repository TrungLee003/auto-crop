from pathlib import Path
from typing import List, Optional
from app.annotation.models import RegionModel, RegionStatus
from app.annotation.service import annotation_service
from app.detection.base import DetectionConfig
from app.detection.registry import detector_registry
from app.detection.task_manager import TaskStatus, task_manager
from app.project.models import PageStatus
from app.project.service import project_service


class DetectionService:
    @staticmethod
    def _get_page_and_project(page_id: str):
        for project in project_service._projects_by_id.values():
            for page in project.pages:
                if page.id == page_id:
                    return page, project
        return None, None

    def detect_page(
        self,
        page_id: str,
        config: Optional[DetectionConfig] = None
    ) -> List[RegionModel]:
        """Runs auto-detection on a single page, saves regions, updates page status."""
        page, project = self._get_page_and_project(page_id)
        if not page or not project:
            raise ValueError(f"Page {page_id} not found")

        detector = detector_registry.get("opencv")
        if not detector:
            raise RuntimeError("Default detector 'opencv' not registered")

        master_path = Path(project.root_path) / page.master_path
        if not master_path.exists():
            raise FileNotFoundError(f"Master image not found at {master_path}")

        # Run detection
        detected_regions = detector.detect(master_path, config)

        # Merge with existing manual annotations if any, or overwrite auto regions
        existing_regions = annotation_service.get_regions(page_id)
        manual_regions = [r for r in existing_regions if r.source != "auto"]

        # Re-sequence combined list
        combined = manual_regions + detected_regions
        for i, r in enumerate(combined, start=1):
            r.sequence = i

        annotation_service.update_regions(page_id, combined)

        # Update page status to IN_REVIEW if not already
        if page.status == PageStatus.NEW:
            page.status = PageStatus.IN_REVIEW
            project_service.save_project(project)

        return combined

    def approve_all_page_regions(self, page_id: str) -> List[RegionModel]:
        """Sets status of all AUTO or EDITED regions on page to APPROVED."""
        regions = annotation_service.get_regions(page_id)
        for r in regions:
            if r.status in (RegionStatus.AUTO, RegionStatus.EDITED):
                r.status = RegionStatus.APPROVED

        annotation_service.update_regions(page_id, regions)
        page, project = self._get_page_and_project(page_id)
        if page and project:
            page.status = PageStatus.REVIEWED
            project_service.save_project(project)

        return regions

    def create_batch_detection_task(
        self,
        project_id: str,
        filter_status: Optional[str] = "NEW",
    ) -> tuple[TaskStatus, List[str]]:
        """Creates task status and gathers target page IDs for batch processing."""
        project = project_service.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Select pages to process
        if filter_status and filter_status != "ALL":
            target_pages = [p for p in project.pages if p.status == filter_status]
        else:
            target_pages = list(project.pages)

        task = task_manager.create_task(
            task_type="batch_detect",
            total_items=len(target_pages),
            message=f"Starting detection on {len(target_pages)} pages...",
        )

        return task, [p.id for p in target_pages]

    def run_batch_detection_job(
        self,
        task_id: str,
        project_id: str,
        page_ids: List[str],
        config: Optional[DetectionConfig]
    ):
        """Synchronous batch worker with error isolation per Section 109."""
        total = len(page_ids)
        failed_count = 0
        for idx, page_id in enumerate(page_ids, start=1):
            if task_manager.is_cancelled(task_id):
                break

            task_manager.update_progress(
                task_id=task_id,
                current_item=idx,
                total_items=total,
                message=f"Processing page {idx}/{total}...",
            )

            try:
                self.detect_page(page_id, config)
            except Exception as e:
                failed_count += 1
                page, project = self._get_page_and_project(page_id)
                if page and project:
                    page.status = PageStatus.FAILED
                    err_msg = f"Detection failed: {str(e)}"
                    if err_msg not in page.warnings:
                        page.warnings.append(err_msg)
                    project_service.save_project(project)

        if not task_manager.is_cancelled(task_id):
            if failed_count > 0:
                task_manager.complete_task(
                    task_id,
                    message=f"Processed {total} pages: {total - failed_count} succeeded, {failed_count} failed"
                )
            else:
                task_manager.complete_task(
                    task_id, message=f"Successfully processed {total} pages"
                )


detection_service = DetectionService()
