from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PageStatus(str, Enum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    DETECTED = "DETECTED"
    IN_REVIEW = "IN_REVIEW"
    REVIEWED = "REVIEWED"
    EXPORTED = "EXPORTED"
    FAILED = "FAILED"


class ImportMode(str, Enum):
    COPY = "COPY"
    REFERENCE = "REFERENCE"


class DetectionSettings(BaseModel):
    provider: str = "opencv"
    profile: str = "historical_line_art"
    sensitivity: float = 0.5
    min_area_ratio: float = 0.0005
    working_long_edge: int = 3500


class EditorSettings(BaseModel):
    default_padding_top: int = 40
    default_padding_right: int = 40
    default_padding_bottom: int = 40
    default_padding_left: int = 40
    autosave_delay_ms: int = 800
    polygon_simplification_tolerance: float = 2.0


class ExportSettings(BaseModel):
    default_preset: str = "archive"
    archive_format: str = "TIFF"
    transparent_png: bool = True
    scale: int = 1


class VectorSettings(BaseModel):
    vectorizer: str = "vtracer"
    preset: str = "conservative"
    colormode: str = "bw"
    filter_speckle: int = 2


class ProjectSettings(BaseModel):
    detection: DetectionSettings = Field(default_factory=DetectionSettings)
    editor: EditorSettings = Field(default_factory=EditorSettings)
    export: ExportSettings = Field(default_factory=ExportSettings)
    vector: VectorSettings = Field(default_factory=VectorSettings)


class PageModel(BaseModel):
    id: str
    project_id: str
    sequence: int
    filename: str
    source_path: str
    master_path: str
    status: PageStatus = PageStatus.NEW
    width: int = 0
    height: int = 0
    dpi: float = 300.0
    bit_depth: int = 8
    bands: int = 3
    file_size_bytes: int = 0
    file_hash: str = ""
    thumbnail_path: Optional[str] = None
    dzi_path: Optional[str] = None
    annotation_path: Optional[str] = None
    region_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProjectSchema(BaseModel):
    schema_version: int = 2
    project_id: str
    name: str
    root_path: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    pages: List[PageModel] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    name: str
    path: Optional[str] = None


class ProjectOpen(BaseModel):
    path: str


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    settings: Optional[ProjectSettings] = None


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    root_path: str
    page_count: int = 0
    created_at: datetime
    updated_at: datetime
    settings: ProjectSettings


class ImportRequest(BaseModel):
    file_paths: List[str] = Field(default_factory=list)
    folder_path: Optional[str] = None
    mode: ImportMode = ImportMode.COPY
    recursive: bool = False


class ImportResult(BaseModel):
    imported_count: int
    skipped_duplicates: int
    failed_count: int
    pages: List[PageModel]
    errors: List[str] = Field(default_factory=list)


class PageViewerInfo(BaseModel):
    page_id: str
    project_id: str
    filename: str
    master_width: int
    master_height: int
    dpi: float
    dzi_url: str
    thumbnail_url: str
