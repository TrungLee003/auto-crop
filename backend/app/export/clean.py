from pathlib import Path
from typing import Tuple
import cv2
import numpy as np
import pyvips

from app.annotation.models import RegionModel
from app.geometry.transforms import apply_padding, compute_bounding_box


def export_clean_crop(
    master_path: Path,
    region: RegionModel,
    output_path: Path,
    dpi: int = 300
) -> Tuple[int, int]:
    """
    Exports clean crop with background removed (transparent alpha PNG).
    Isolates ink strokes, applies antialiased alpha masking, and saves as 32-bit RGBA PNG.
    """
    master_img = pyvips.Image.new_from_file(str(master_path))
    bounds = compute_bounding_box(region.geometry)
    crop_x, crop_y, crop_w, crop_h = apply_padding(
        bounds, region.padding, max_w=master_img.width, max_h=master_img.height
    )

    crop_vips = master_img.crop(crop_x, crop_y, crop_w, crop_h)
    if crop_vips.bands > 3:
        crop_vips = crop_vips.extract_band(0, n=3)
    crop_np = crop_vips.numpy()

    if len(crop_np.shape) == 3 and crop_np.shape[2] >= 3:
        gray = cv2.cvtColor(crop_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = crop_np.copy()

    # 1. Background Normalization
    bg_size = 41
    kernel_bg = cv2.getStructuringElement(cv2.MORPH_RECT, (bg_size, bg_size))
    background = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel_bg)
    diff = cv2.absdiff(background, gray)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    # 2. Ink Mask
    _, ink_mask = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 3. Smooth & Feather Alpha
    alpha = cv2.GaussianBlur(ink_mask, (3, 3), 0.5)

    # 4. If polygon, mask outside polygon
    if region.geometry.type == "polygon":
        poly_pts = region.geometry.points
        rel_pts = np.array(
            [[p[0] - crop_x, p[1] - crop_y] for p in poly_pts],
            dtype=np.int32
        )
        poly_mask = np.zeros((crop_h, crop_w), dtype=np.uint8)
        cv2.fillPoly(poly_mask, [rel_pts], 255)
        alpha = cv2.bitwise_and(alpha, poly_mask)

    # 5. Assemble RGBA image
    if len(crop_np.shape) == 3 and crop_np.shape[2] >= 3:
        rgba = cv2.cvtColor(crop_np, cv2.COLOR_RGB2RGBA)
    else:
        rgba = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGBA)

    rgba[:, :, 3] = alpha

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Save with OpenCV / PIL for clean RGBA transparency
    cv2.imwrite(str(output_path), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))

    return crop_w, crop_h
