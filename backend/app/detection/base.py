from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from app.annotation.models import RegionModel


class DetectionConfig(BaseModel):
    preset: str = "historical_line_art"  # "historical_line_art" | "dense_woodcut" | "custom"
    target_long_edge: int = 3500
    sensitivity: float = 0.5  # 0.0 to 1.0
    min_area_ratio: float = 0.001  # Min 0.1% of page area
    max_area_ratio: float = 0.92  # Max 92% of page area
    text_suppression: bool = True
    merge_distance: int = 35
    padding_default: int = 40
    min_confidence: float = 0.5


class Detector(ABC):
    @abstractmethod
    def detect(self, master_path: Path, config: Optional[DetectionConfig] = None) -> List[RegionModel]:
        """Detect illustrations on a master scan image and return RegionModel candidates."""
        pass
