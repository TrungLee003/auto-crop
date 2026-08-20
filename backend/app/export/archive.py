import math
from pathlib import Path
from typing import Tuple
import cv2
import numpy as np
import pyvips

from app.annotation.models import PolygonGeometry, RegionModel
from app.geometry.transforms import apply_padding, compute_bounding_box


def export_archive_crop(
    master_path: Path,
    region: RegionModel,
    output_path: Path,
    dpi: int = 300
) -> Tuple[int, int]:
    """
    Exports full master-resolution archive crop.
    Preserves scan DPI, color profile, and handles polygon alpha clipping if applicable.
    Returns (width, height) of exported crop.
    """
    master_img = pyvips.Image.new_from_file(str(master_path))
    bounds = compute_bounding_box(region.geometry)
    crop_x, crop_y, crop_w, crop_h = apply_padding(
        bounds, region.padding, max_w=master_img.width, max_h=master_img.height
    )

    crop_img = master_img.crop(crop_x, crop_y, crop_w, crop_h)

    # If region is a polygon, create an anti-aliased alpha mask
    if region.geometry.type == "polygon":
        poly_pts = region.geometry.points
        rel_pts = np.array(
            [[p[0] - crop_x, p[1] - crop_y] for p in poly_pts],
            dtype=np.int32
        )
        mask = np.zeros((crop_h, crop_w), dtype=np.uint8)
        cv2.fillPoly(mask, [rel_pts], 255)
        mask = cv2.GaussianBlur(mask, (3, 3), 0.5)

        mask_vips = pyvips.Image.new_from_memory(
            mask.tobytes(), crop_w, crop_h, 1, "uchar"
        )
        if crop_img.bands == 3:
            crop_img = crop_img.bandjoin(mask_vips)
        elif crop_img.bands == 4:
            crop_img = crop_img.extract_band(0, n=3).bandjoin(mask_vips)

    # Set DPI metadata (pyvips uses pixels/mm: 300 DPI = ~11.811 px/mm)
    px_per_mm = dpi / 25.4
    crop_img = crop_img.copy(xres=px_per_mm, yres=px_per_mm)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ext = output_path.suffix.lower()

    if ext in (".tif", ".tiff"):
        crop_img.tiffsave(str(output_path), compression="deflate", resunit="inch", xres=dpi, yres=dpi)
    else:
        crop_img.pngsave(str(output_path), compression=6)

    return crop_w, crop_h
