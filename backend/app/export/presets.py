from pydantic import BaseModel

class ExportPreset(BaseModel):
    name: str
    format: str
    dpi: int
    quality: int

ARCHIVE_PRESET = ExportPreset(name="archive", format="tiff", dpi=600, quality=100)
DESIGN_PRESET = ExportPreset(name="design", format="png", dpi=300, quality=100)
VECTOR_PRESET = ExportPreset(name="vector", format="svg", dpi=300, quality=100)
