import re
import time
from pathlib import Path
from typing import Any, Dict, Optional
import vtracer

from .base import Vectorizer, VectorResult


class PotraceVectorizer(Vectorizer):
    """
    Fallback Vectorizer provider for monochrome binary line-art.
    Uses binary threshold tracing.
    """
    def vectorize(
        self,
        raster_path: Path,
        output_svg_path: Path,
        settings: Optional[Dict[str, Any]] = None,
    ) -> VectorResult:
        s = settings or {}
        output_svg_path.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.perf_counter()
        vtracer.convert_image_to_svg_py(
            str(raster_path),
            str(output_svg_path),
            colormode="binary",
            mode="polygon",
            filter_speckle=int(s.get("filter_speckle", 4)),
            color_precision=6,
            layer_difference=16,
            corner_threshold=int(s.get("corner_threshold", 60)),
            length_threshold=float(s.get("length_threshold", 4.0)),
            max_iterations=10,
            splice_threshold=45,
            path_precision=int(s.get("path_precision", 3)),
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

