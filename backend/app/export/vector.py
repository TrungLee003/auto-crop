import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import vtracer

from app.annotation.models import RegionModel
from app.export.clean import export_clean_crop


class VTracerParams(BaseModel):
    colormode: str = "bw"  # "bw" | "color" | "binary"
    mode: str = "spline"  # "spline" | "polygon" | "none"
    filter_speckle: int = 4
    color_precision: int = 6
    layer_difference: int = 16
    corner_threshold: int = 60
    length_threshold: float = 4.0
    max_iterations: int = 10
    splice_threshold: int = 45
    path_precision: int = 3


class VTracerPreset(BaseModel):
    id: str
    name: str
    description: str
    params: VTracerParams


BUILTIN_PRESETS: Dict[str, VTracerPreset] = {
    "historical_bw": VTracerPreset(
        id="historical_bw",
        name="Historical B/W Woodcut",
        description="Optimized for classic woodcuts, block prints, and book illustrations.",
        params=VTracerParams(
            colormode="bw",
            mode="spline",
            filter_speckle=4,
            color_precision=6,
            layer_difference=16,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=10,
            splice_threshold=45,
            path_precision=3,
        ),
    ),
    "detailed_engraving": VTracerPreset(
        id="detailed_engraving",
        name="Detailed Engraving & Etching",
        description="Preserves fine cross-hatch lines and delicate architectural details.",
        params=VTracerParams(
            colormode="bw",
            mode="spline",
            filter_speckle=2,
            color_precision=8,
            layer_difference=8,
            corner_threshold=45,
            length_threshold=2.0,
            max_iterations=15,
            splice_threshold=30,
            path_precision=5,
        ),
    ),
    "color_lithograph": VTracerPreset(
        id="color_lithograph",
        name="Color Lithograph / Plate",
        description="Multi-color vector tracing for colorized plates and illuminated manuscripts.",
        params=VTracerParams(
            colormode="color",
            mode="spline",
            filter_speckle=4,
            color_precision=8,
            layer_difference=16,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=10,
            splice_threshold=45,
            path_precision=3,
        ),
    ),
}


def export_vector_svg(
    raster_image_path: Path,
    output_svg_path: Path,
    params: Optional[VTracerParams] = None,
    provider: str = "vtracer"
) -> bool:
    """
    Vectorizes a raster illustration into genuine SVG vector paths using VectorizerRegistry.
    Produces clean spline curves with no embedded raster images.
    """
    from app.vector.registry import vectorizer_registry
    p = params or BUILTIN_PRESETS["historical_bw"].params
    vectorizer = vectorizer_registry.get(provider) or vectorizer_registry.get("vtracer")
    if not vectorizer:
        raise RuntimeError(f"Vectorizer '{provider}' not available")

    vectorizer.vectorize(
        raster_path=raster_image_path,
        output_svg_path=output_svg_path,
        settings=p.model_dump()
    )
    return True


def generate_vector_preview(
    master_path: Path,
    region: RegionModel,
    preset_id: str = "historical_bw",
    custom_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates live SVG vector preview for a region with timing and metrics.
    """
    if preset_id in BUILTIN_PRESETS:
        params_dict = BUILTIN_PRESETS[preset_id].params.model_dump()
    else:
        params_dict = BUILTIN_PRESETS["historical_bw"].params.model_dump()

    if custom_params:
        params_dict.update(custom_params)

    params = VTracerParams(**params_dict)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        clean_png = tmp_path / "clean.png"
        vector_svg = tmp_path / "preview.svg"

        # 1. Extract clean raster
        w, h = export_clean_crop(master_path, region, clean_png, dpi=300)

        # 2. Vectorize with timing
        t0 = time.perf_counter()
        export_vector_svg(clean_png, vector_svg, params=params)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        svg_content = vector_svg.read_text(encoding="utf-8")
        file_size_bytes = len(svg_content.encode("utf-8"))

        # Count <path> elements
        path_count = len(re.findall(r"<path\b", svg_content, re.IGNORECASE))

        return {
            "svg_content": svg_content,
            "path_count": path_count,
            "width": w,
            "height": h,
            "file_size_bytes": file_size_bytes,
            "elapsed_ms": elapsed_ms,
            "preset_id": preset_id,
            "params": params.model_dump(),
        }
