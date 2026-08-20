import re
import time
from pathlib import Path
from typing import Any, Dict, Optional
import vtracer

from .base import Vectorizer, VectorResult


class VTracerVectorizer(Vectorizer):
    """
    Vectorizer provider using VisionCortex VTracer.
    Traces raster images into smooth spline SVG vector paths.
    """
    def vectorize(
        self,
        raster_path: Path,
        output_svg_path: Path,
        settings: Optional[Dict[str, Any]] = None,
    ) -> VectorResult:
        s = settings or {}
        output_svg_path.parent.mkdir(parents=True, exist_ok=True)

        colormode = s.get("colormode", "bw")
        mode = s.get("mode", "spline")
        filter_speckle = int(s.get("filter_speckle", 4))
        color_precision = int(s.get("color_precision", 6))
        layer_difference = int(s.get("layer_difference", 16))
        corner_threshold = int(s.get("corner_threshold", 60))
        length_threshold = float(s.get("length_threshold", 4.0))
        max_iterations = int(s.get("max_iterations", 10))
        splice_threshold = int(s.get("splice_threshold", 45))
        path_precision = int(s.get("path_precision", 3))

        t0 = time.perf_counter()
        vtracer.convert_image_to_svg_py(
            str(raster_path),
            str(output_svg_path),
            colormode=colormode,
            mode=mode,
            filter_speckle=filter_speckle,
            color_precision=color_precision,
            layer_difference=layer_difference,
            corner_threshold=corner_threshold,
            length_threshold=length_threshold,
            max_iterations=max_iterations,
            splice_threshold=splice_threshold,
            path_precision=path_precision,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        svg_content = output_svg_path.read_text(encoding="utf-8") if output_svg_path.exists() else ""
        path_count = len(re.findall(r"<path\b", svg_content, re.IGNORECASE))
        file_size = len(svg_content.encode("utf-8"))

        return VectorResult(
            path=str(output_svg_path),
            format="svg",
            path_count=path_count,
            file_size_bytes=file_size,
            elapsed_ms=elapsed_ms,
        )

