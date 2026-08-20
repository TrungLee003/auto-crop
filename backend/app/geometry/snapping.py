from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np
import pyvips

from app.annotation.models import (
    PolygonGeometry,
    RectangleGeometry,
    RegionGeometry,
    RotatedRectangleGeometry,
)
from app.geometry.transforms import compute_bounding_box


def fit_region_to_ink_content(
    master_path: Path,
    geometry: RegionGeometry,
    padding_margin: int = 20
) -> RegionGeometry:
    """
    Tightly fits a region around the actual illustration/ink content.
    1. Extracts region crop with context margin.
    2. Isolates ink using background subtraction + Otsu thresholding.
    3. Finds minimum bounding box or convex hull of ink strokes.
    4. Offsets coordinates back to master image space.
    """
    min_x, min_y, max_x, max_y = compute_bounding_box(geometry)
    
    # Context window around region
    margin = 40
    crop_x = max(0, int(min_x - margin))
    crop_y = max(0, int(min_y - margin))
    crop_w = int(max_x - min_x + margin * 2)
    crop_h = int(max_y - min_y + margin * 2)

    # Load patch using pyvips
    master_img = pyvips.Image.new_from_file(str(master_path))
    crop_w = min(crop_w, master_img.width - crop_x)
    crop_h = min(crop_h, master_img.height - crop_y)

    if crop_w <= 10 or crop_h <= 10:
        return geometry

    # Extract crop to numpy array
    patch = master_img.crop(crop_x, crop_y, crop_w, crop_h)
    patch_np = patch.numpy()

    if len(patch_np.shape) == 3:
        gray = cv2.cvtColor(patch_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = patch_np.copy()

    # 1. Background Normalization
    kernel_bg = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31))
    background = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel_bg)
    diff = cv2.absdiff(background, gray)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    # 2. Ink Mask
    _, ink_mask = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 3. Filter noise
    kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    clean = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN, kernel_clean)

    # 4. Find non-zero ink pixels
    points = cv2.findNonZero(clean)
    if points is None or len(points) < 50:
        return geometry

    # Compute bounding rect of ink
    ix, iy, iw, ih = cv2.boundingRect(points)

    # Convert back to master pixel coordinates
    master_fit_x = crop_x + ix - padding_margin
    master_fit_y = crop_y + iy - padding_margin
    master_fit_w = iw + padding_margin * 2
    master_fit_h = ih + padding_margin * 2

    # Clamp to master bounds
    master_fit_x = max(0, min(master_img.width - 1, master_fit_x))
    master_fit_y = max(0, min(master_img.height - 1, master_fit_y))
    master_fit_w = min(master_fit_w, master_img.width - master_fit_x)
    master_fit_h = min(master_fit_h, master_img.height - master_fit_y)

    if geometry.type == "rotated_rectangle":
        cx = master_fit_x + master_fit_w / 2.0
        cy = master_fit_y + master_fit_h / 2.0
        return RotatedRectangleGeometry(
            cx=cx,
            cy=cy,
            width=master_fit_w,
            height=master_fit_h,
            angle=geometry.angle
        )
    elif geometry.type == "polygon":
        # Return rectangular polygon or convex hull
        hull = cv2.convexHull(points)
        if len(hull) >= 3:
            hull_pts = [[float(crop_x + p[0][0]), float(crop_y + p[0][1])] for p in hull]
            return PolygonGeometry(points=hull_pts)

    return RectangleGeometry(
        x=master_fit_x,
        y=master_fit_y,
        width=master_fit_w,
        height=master_fit_h
    )
