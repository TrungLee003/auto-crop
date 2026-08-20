from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.project.models import utc_now


class ExportScope(str, Enum):
    APPROVED_ONLY = "APPROVED_ONLY"
    ALL_EXCEPT_REJECTED = "ALL_EXCEPT_REJECTED"
    ALL = "ALL"


class ExportFormatOptions(BaseModel):
    archive: bool = True
    clean: bool = True
    vector: bool = True


class ExportRequest(BaseModel):
    scope: ExportScope = ExportScope.APPROVED_ONLY
    formats: ExportFormatOptions = Field(default_factory=ExportFormatOptions)
    archive_format: str = "PNG"  # "PNG" | "TIFF"
    custom_output_dir: Optional[str] = None


class RegionExportMetadata(BaseModel):
    export_version: int = 2
    project_id: str
    project_name: str
    page_id: str
    page_filename: str
    page_sequence: int
    region_id: str
    region_sequence: int
    geometry_type: str
    crop_bounds: Dict[str, float]
    dpi: int = 300
    status: str
    export_files: Dict[str, str] = Field(default_factory=dict)
    exported_at: datetime = Field(default_factory=utc_now)


class ExportJobSummary(BaseModel):
    export_id: str
    export_dir: str
    total_regions: int
    archive_count: int = 0
    clean_count: int = 0
    vector_count: int = 0
    exported_at: datetime = Field(default_factory=utc_now)
