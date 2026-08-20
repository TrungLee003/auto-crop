from typing import Dict, List, Optional
from app.detection.base import Detector
from app.detection.opencv import OpenCVDetector


class DetectorRegistry:
    def __init__(self):
        self._detectors: Dict[str, Detector] = {}
        # Register default OpenCV detector
        self.register("opencv", OpenCVDetector())

    def register(self, name: str, detector: Detector):
        self._detectors[name] = detector

    def get(self, name: str = "opencv") -> Optional[Detector]:
        return self._detectors.get(name)

    def list_providers(self) -> List[str]:
        return list(self._detectors.keys())


detector_registry = DetectorRegistry()
