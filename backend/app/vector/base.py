from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel


class VectorResult(BaseModel):
    path: str
    format: str = "svg"
    path_count: int = 0
    file_size_bytes: int = 0
    elapsed_ms: float = 0.0


class Vectorizer(ABC):
    @abstractmethod
    def vectorize(
        self,
        raster_path: Path,
        output_svg_path: Path,
        settings: Optional[Dict[str, Any]] = None,
    ) -> VectorResult:
        pass
