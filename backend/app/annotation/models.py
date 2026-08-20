from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field
from app.project.models import utc_now


class RegionStatus(str, Enum):
    AUTO = "AUTO"
    EDITED = "EDITED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Padding(BaseModel):
    top: int = 40
    right: int = 40
    bottom: int = 40
    left: int = 40


class RegionExportSettings(BaseModel):
    archive: bool = True
    clean: bool = True
    vector: bool = False


class RectangleGeometry(BaseModel):
    type: Literal["rectangle"] = "rectangle"
    x: float
    y: float
    width: float
    height: float


class RotatedRectangleGeometry(BaseModel):
    type: Literal["rotated_rectangle"] = "rotated_rectangle"
    cx: float
    cy: float
    width: float
    height: float
    angle: float = 0.0


class PolygonGeometry(BaseModel):
    type: Literal["polygon"] = "polygon"
    points: List[List[float]]


class MultiPolygonGeometry(BaseModel):
    type: Literal["multipolygon"] = "multipolygon"
    polygons: List[List[List[float]]]


RegionGeometry = Union[
    RectangleGeometry,
    RotatedRectangleGeometry,
    PolygonGeometry,
    MultiPolygonGeometry,
]


class RegionModel(BaseModel):
    id: str
    sequence: int
    geometry: RegionGeometry = Field(discriminator="type")
    source: str = "manual"  # "auto" | "manual"
    status: RegionStatus = RegionStatus.EDITED
    name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    padding: Padding = Field(default_factory=Padding)
    export: RegionExportSettings = Field(default_factory=RegionExportSettings)
    confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PageAnnotationsSchema(BaseModel):
    schema_version: int = 2
    page_id: str
    regions: List[RegionModel] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)
