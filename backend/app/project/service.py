import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.images.deepzoom import DeepZoomService
from app.images.master import MasterService
from app.images.thumbnail import ThumbnailService
from app.project.models import (
    ImportMode,
    ImportResult,
    PageModel,
    PageStatus,
    ProjectResponse,
    ProjectSchema,
    ProjectSettings,
    utc_now,
)
import re


def natural_sort_key(s: str) -> List[object]:
    """Natural alphanumeric sort key, so 'page-2.jpg' sorts before 'page-10.jpg'."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s or ""))]



class ProjectService:
    def __init__(self):
        # Cache of loaded projects by project_id and by root_path
        self._projects_by_id: Dict[str, ProjectSchema] = {}
        self._projects_by_path: Dict[str, ProjectSchema] = {}

    def create_project(self, name: str, root_path: Optional[str] = None) -> ProjectSchema:
        """Create a new project folder and initialize its structure."""
        proj_id = str(uuid.uuid4())
        
        if root_path:
            project_dir = Path(root_path)
        else:
            # Default to current working dir / projects / {name}
            project_dir = Path.cwd() / "projects" / name.replace(" ", "_")

        project_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (project_dir / "sources").mkdir(parents=True, exist_ok=True)
        (project_dir / "masters").mkdir(parents=True, exist_ok=True)
        (project_dir / "annotations").mkdir(parents=True, exist_ok=True)
        (project_dir / "cache" / "thumbnails").mkdir(parents=True, exist_ok=True)
        (project_dir / "cache" / "deepzoom").mkdir(parents=True, exist_ok=True)
        (project_dir / "cache" / "masks").mkdir(parents=True, exist_ok=True)
        (project_dir / "exports" / "archive").mkdir(parents=True, exist_ok=True)
        (project_dir / "exports" / "clean").mkdir(parents=True, exist_ok=True)
        (project_dir / "exports" / "vector").mkdir(parents=True, exist_ok=True)
        (project_dir / "logs").mkdir(parents=True, exist_ok=True)

        project = ProjectSchema(
            schema_version=2,
            project_id=proj_id,
            name=name,
            root_path=str(project_dir.resolve()),
            created_at=utc_now(),
            updated_at=utc_now(),
            settings=ProjectSettings(),
            pages=[]
        )

        self.save_project(project)
        self._projects_by_id[proj_id] = project
        self._projects_by_path[str(project_dir.resolve())] = project

        return project

    def open_project(self, path_str: str) -> ProjectSchema:
        """Open an existing project from directory path."""
        proj_path = Path(path_str).resolve()
        json_file = proj_path / "project.json"

        if not json_file.exists():
            raise FileNotFoundError(f"No project.json found at {proj_path}")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        project = ProjectSchema(**data)
        project.root_path = str(proj_path)

        self._projects_by_id[project.project_id] = project
        self._projects_by_path[str(proj_path)] = project

        return project

    def save_project(self, project: ProjectSchema) -> None:
        """Atomic save of project.json."""
        proj_dir = Path(project.root_path)
        target_file = proj_dir / "project.json"
        tmp_file = proj_dir / "project.json.tmp"

        project.updated_at = utc_now()
        data = project.model_dump(mode="json")

        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # Atomic replacement on Windows / POSIX
        if target_file.exists():
            target_file.unlink()
        tmp_file.rename(target_file)

    def get_project(self, project_id: str) -> Optional[ProjectSchema]:
        """Get project by ID."""
        return self._projects_by_id.get(project_id)

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        settings: Optional[ProjectSettings] = None
    ) -> ProjectSchema:
        """Update project name or settings and persist changes."""
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        if name is not None:
            project.name = name
        if settings is not None:
            project.settings = settings

        self.save_project(project)
        return project

    def delete_project(self, project_id: str, delete_files: bool = False) -> bool:
        """Remove project from memory and optionally remove files from disk."""
        project = self.get_project(project_id)
        if not project:
            return False

        # Remove from in-memory caches
        self._projects_by_id.pop(project_id, None)
        if project.root_path in self._projects_by_path:
            self._projects_by_path.pop(project.root_path, None)

        if delete_files:
            proj_dir = Path(project.root_path)
            if proj_dir.exists() and proj_dir.is_dir():
                shutil.rmtree(proj_dir, ignore_errors=True)

        return True

    def delete_page(self, project_id: str, page_id: str, delete_files: bool = True) -> bool:
        """Delete a single page from project and clean up its cached assets."""
        project = self.get_project(project_id)
        if not project:
            return False

        page_idx = next((i for i, p in enumerate(project.pages) if p.id == page_id), None)
        if page_idx is None:
            return False

        page = project.pages.pop(page_idx)
        project_root = Path(project.root_path)

        if delete_files:
            # 1. Clean annotations
            anno_file = project_root / "annotations" / f"{page_id}.json"
            if anno_file.exists():
                anno_file.unlink()
            anno_bak = project_root / "annotations" / f"{page_id}.json.bak"
            if anno_bak.exists():
                anno_bak.unlink()

            # 2. Clean thumbnail
            if page.thumbnail_path:
                thumb_file = project_root / page.thumbnail_path
                if thumb_file.exists():
                    thumb_file.unlink()

            # 3. Clean DeepZoom DZI & pyramid tiles
            dzi_file = project_root / "cache" / "deepzoom" / f"{page_id}.dzi"
            if dzi_file.exists():
                dzi_file.unlink()
            dzi_files_dir = project_root / "cache" / "deepzoom" / f"{page_id}_files"
            if dzi_files_dir.exists():
                shutil.rmtree(dzi_files_dir, ignore_errors=True)

        # Re-sequence remaining pages
        for idx, p in enumerate(project.pages, start=1):
            p.sequence = idx

        self.save_project(project)
        return True

    def list_projects(self) -> List[ProjectResponse]:
        """List currently loaded projects."""
        return [
            ProjectResponse(
                project_id=p.project_id,
                name=p.name,
                root_path=p.root_path,
                page_count=len(p.pages),
                created_at=p.created_at,
                updated_at=p.updated_at,
                settings=p.settings
            )
            for p in self._projects_by_id.values()
        ]

    def import_scans(
        self,
        project_id: str,
        file_paths: List[str],
        folder_path: Optional[str] = None,
        mode: ImportMode = ImportMode.COPY,
        recursive: bool = False
    ) -> ImportResult:
        """
        Import multiple image files or a folder into the project.
        Extracts metadata, creates masters, generates thumbnails and DeepZoom pyramids.
        """
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        project_root = Path(project.root_path)
        all_candidate_files: List[Path] = []

        # Collect files from individual paths
        for fp in file_paths:
            p = Path(fp)
            if p.is_file() and MasterService.is_supported_image(p):
                all_candidate_files.append(p)

        # Collect files from folder if provided
        if folder_path:
            f_dir = Path(folder_path)
            if f_dir.is_dir():
                pattern = "**/*" if recursive else "*"
                for p in f_dir.glob(pattern):
                    if p.is_file() and MasterService.is_supported_image(p):
                        all_candidate_files.append(p)

        # Deduplicate candidates against each other by resolved path
        seen_paths = set()
        unique_candidates: List[Path] = []
        for p in all_candidate_files:
            resolved = str(p.resolve())
            if resolved not in seen_paths:
                seen_paths.add(resolved)
                unique_candidates.append(p)

        # Sort naturally (e.g. page-1.jpg, page-2.jpg, ... page-10.jpg, page-100.jpg)
        unique_candidates.sort(key=lambda p: natural_sort_key(p.name))

        # Existing hashes and filenames in project for deduplication
        existing_hashes = {p.file_hash for p in project.pages if p.file_hash}

        imported_pages: List[PageModel] = []
        skipped_count = 0
        failed_count = 0
        errors: List[str] = []

        seq = len(project.pages) + 1

        for src_file in unique_candidates:
            try:
                # Fast check hash
                f_hash = MasterService.compute_file_hash(src_file)
                if f_hash in existing_hashes:
                    skipped_count += 1
                    continue

                page_id = str(uuid.uuid4())[:8] # short human-friendly page identifier
                copy_source = (mode == ImportMode.COPY)

                # Process master
                rel_src, rel_master, meta = MasterService.create_master_from_source(
                    source_path=src_file,
                    project_root=project_root,
                    page_id=page_id,
                    copy_source=copy_source
                )

                master_abs = project_root / rel_master

                # Generate thumbnail
                rel_thumb = ThumbnailService.generate_thumbnail(
                    master_path=master_abs,
                    project_root=project_root,
                    page_id=page_id,
                    target_long_edge=320
                )

                # Generate DeepZoom pyramid
                rel_dzi = DeepZoomService.generate_dzi(
                    master_path=master_abs,
                    project_root=project_root,
                    page_id=page_id,
                    tile_size=256,
                    overlap=1
                )

                # Initialize empty annotation file
                rel_anno = Path("annotations") / f"{page_id}.json"
                anno_abs = project_root / rel_anno
                if not anno_abs.exists():
                    with open(anno_abs, "w", encoding="utf-8") as af:
                        json.dump({"page_id": page_id, "regions": []}, af)

                page = PageModel(
                    id=page_id,
                    project_id=project_id,
                    sequence=seq,
                    filename=src_file.name,
                    source_path=str(rel_src).replace("\\", "/"),
                    master_path=str(rel_master).replace("\\", "/"),
                    status=PageStatus.NEW,
                    width=meta["width"],
                    height=meta["height"],
                    dpi=meta["dpi"],
                    bit_depth=meta["bit_depth"],
                    bands=meta["bands"],
                    file_size_bytes=meta["file_size_bytes"],
                    file_hash=f_hash,
                    thumbnail_path=str(rel_thumb).replace("\\", "/"),
                    dzi_path=str(rel_dzi).replace("\\", "/"),
                    annotation_path=str(rel_anno).replace("\\", "/"),
                    region_count=0,
                    warnings=[],
                    created_at=utc_now(),
                    updated_at=utc_now()
                )

                project.pages.append(page)
                imported_pages.append(page)
                existing_hashes.add(f_hash)
                seq += 1

            except Exception as e:
                failed_count += 1
                errors.append(f"Failed to import {src_file.name}: {str(e)}")

        # Save project changes
        if imported_pages:
            self.save_project(project)

        return ImportResult(
            imported_count=len(imported_pages),
            skipped_duplicates=skipped_count,
            failed_count=failed_count,
            pages=imported_pages,
            errors=errors
        )

    def sort_pages(self, project_id: str) -> ProjectSchema:
        """Sort all pages in natural alphanumeric filename order and re-sequence 1..N."""
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        project.pages.sort(key=lambda p: natural_sort_key(p.filename))
        for idx, p in enumerate(project.pages, start=1):
            p.sequence = idx
        self.save_project(project)
        return project


# Global singleton instance
project_service = ProjectService()

