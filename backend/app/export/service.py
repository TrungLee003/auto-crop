import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.annotation.models import RegionModel, RegionStatus
from app.annotation.service import annotation_service
from app.detection.task_manager import TaskStatus, task_manager
from app.export.archive import export_archive_crop
from app.export.clean import export_clean_crop
from app.export.manifest import generate_catalog_csv, write_region_metadata_json
from app.export.models import (
    ExportJobSummary,
    ExportRequest,
    ExportScope,
    RegionExportMetadata,
)
from app.export.vector import export_vector_svg
from app.geometry.transforms import compute_bounding_box
from app.project.models import PageModel, ProjectSchema, utc_now
from app.project.service import project_service


class ExportService:
    def create_export_job(
        self,
        project_id: str,
        req: ExportRequest
    ) -> Tuple[TaskStatus, Path, List[Tuple[PageModel, RegionModel]]]:
        project = project_service.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        project_root = Path(project.root_path)

        # Setup export directory
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        if req.custom_output_dir:
            export_dir = Path(req.custom_output_dir)
        else:
            export_dir = project_root / "exports" / f"export_{timestamp_str}"
        export_dir.mkdir(parents=True, exist_ok=True)

        # Gather target regions based on scope
        target_items: List[Tuple[PageModel, RegionModel]] = []
        for page in project.pages:
            regions = annotation_service.get_regions(page.id)
            for r in regions:
                if req.scope == ExportScope.APPROVED_ONLY and r.status != RegionStatus.APPROVED:
                    continue
                if req.scope == ExportScope.ALL_EXCEPT_REJECTED and r.status == RegionStatus.REJECTED:
                    continue
                target_items.append((page, r))

        task = task_manager.create_task(
            task_type="export",
            total_items=len(target_items),
            message=f"Starting export of {len(target_items)} illustrations...",
        )

        return task, export_dir, target_items

    def run_export_job(
        self,
        task_id: str,
        project_id: str,
        export_dir: Path,
        target_items: List[Tuple[PageModel, RegionModel]],
        req: ExportRequest
    ):
        project = project_service.get_project(project_id)
        if not project:
            return

        project_root = Path(project.root_path)
        safe_proj_name = "".join(c if c.isalnum() else "_" for c in project.name)

        archive_dir = export_dir / "archive"
        clean_dir = export_dir / "clean"
        vector_dir = export_dir / "vector"
        meta_dir = export_dir / "metadata"

        catalog_records: List[Dict[str, Any]] = []
        total = len(target_items)

        archive_count = 0
        clean_count = 0
        vector_count = 0

        for idx, (page, region) in enumerate(target_items, start=1):
            if task_manager.is_cancelled(task_id):
                break

            task_manager.update_progress(
                task_id=task_id,
                current_item=idx,
                total_items=total,
                message=f"Exporting illustration {idx}/{total}...",
            )

            master_path = project_root / page.master_path
            if not master_path.exists():
                continue

            base_name = f"{safe_proj_name}_{page.sequence:04d}_{region.sequence:02d}"
            export_files = {}

            # 1. Archive Stream
            if req.formats.archive and region.export.archive:
                ext = ".tif" if req.archive_format.upper() == "TIFF" else ".png"
                archive_file = archive_dir / f"{base_name}_archive{ext}"
                try:
                    w, h = export_archive_crop(master_path, region, archive_file, dpi=page.dpi or 300)
                    export_files["archive"] = str(archive_file.relative_to(export_dir))
                    archive_count += 1
                except Exception as e:
                    print(f"Archive export error: {e}")

            # 2. Clean Stream
            clean_file = None
            if req.formats.clean and region.export.clean:
                clean_file = clean_dir / f"{base_name}_clean.png"
                try:
                    w, h = export_clean_crop(master_path, region, clean_file, dpi=page.dpi or 300)
                    export_files["clean"] = str(clean_file.relative_to(export_dir))
                    clean_count += 1
                except Exception as e:
                    print(f"Clean export error: {e}")

            # 3. Vector Stream
            if req.formats.vector:
                vector_file = vector_dir / f"{base_name}_vector.svg"
                try:
                    # Use clean PNG if available, else generate clean crop temporarily
                    raster_src = clean_file
                    temp_raster = False
                    if not raster_src or not raster_src.exists():
                        raster_src = export_dir / f"_tmp_{base_name}.png"
                        export_clean_crop(master_path, region, raster_src, dpi=300)
                        temp_raster = True

                    export_vector_svg(raster_src, vector_file)
                    export_files["vector"] = str(vector_file.relative_to(export_dir))
                    vector_count += 1

                    if temp_raster and raster_src.exists():
                        raster_src.unlink()
                except Exception as e:
                    print(f"Vector export error: {e}")

            # 4. Metadata JSON Sidecar
            min_x, min_y, max_x, max_y = compute_bounding_box(region.geometry)
            meta = RegionExportMetadata(
                project_id=project_id,
                project_name=project.name,
                page_id=page.id,
                page_filename=page.filename,
                page_sequence=page.sequence,
                region_id=region.id,
                region_sequence=region.sequence,
                geometry_type=region.geometry.type,
                crop_bounds={
                    "min_x": float(min_x),
                    "min_y": float(min_y),
                    "max_x": float(max_x),
                    "max_y": float(max_y),
                    "width": float(max_x - min_x),
                    "height": float(max_y - min_y),
                },
                dpi=page.dpi or 300,
                status=str(region.status),
                export_files=export_files,
                exported_at=utc_now(),
            )
            meta_file = meta_dir / f"{base_name}_metadata.json"
            write_region_metadata_json(meta, meta_file)

            # 5. Catalog Record
            catalog_records.append({
                "page_sequence": page.sequence,
                "illustration_sequence": region.sequence,
                "name": region.name or f"Illustration #{region.sequence}",
                "width_px": round(max_x - min_x),
                "height_px": round(max_y - min_y),
                "dpi": page.dpi or 300,
                "archive_file": export_files.get("archive", ""),
                "clean_file": export_files.get("clean", ""),
                "vector_file": export_files.get("vector", ""),
            })

        # Generate catalog.csv
        generate_catalog_csv(catalog_records, export_dir / "catalog.csv")

        # Save export summary JSON in export dir
        summary = ExportJobSummary(
            export_id=export_dir.name,
            export_dir=str(export_dir),
            total_regions=len(catalog_records),
            archive_count=archive_count,
            clean_count=clean_count,
            vector_count=vector_count,
            exported_at=utc_now(),
        )
        with open(export_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary.model_dump(mode="json"), f, indent=2)

        if not task_manager.is_cancelled(task_id):
            task_manager.complete_task(
                task_id, message=f"Export completed: {len(catalog_records)} illustrations exported"
            )

    def list_project_exports(self, project_id: str) -> List[ExportJobSummary]:
        project = project_service.get_project(project_id)
        if not project:
            return []

        exports_root = Path(project.root_path) / "exports"
        if not exports_root.exists():
            return []

        summaries = []
        for exp_dir in sorted(exports_root.iterdir(), reverse=True):
            if exp_dir.is_dir() and (exp_dir / "summary.json").exists():
                try:
                    with open(exp_dir / "summary.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    summaries.append(ExportJobSummary(**data))
                except Exception:
                    pass

        return summaries


export_service = ExportService()
