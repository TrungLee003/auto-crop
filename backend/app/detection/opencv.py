import math
import uuid
from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np
import pyvips

from app.annotation.models import (
    Padding,
    RectangleGeometry,
    RegionExportSettings,
    RegionModel,
    RegionStatus,
)
from app.detection.base import DetectionConfig, Detector
from app.project.models import utc_now


class OpenCVDetector(Detector):
    def detect(self, master_path: Path, config: Optional[DetectionConfig] = None) -> List[RegionModel]:
        if config is None:
            config = DetectionConfig()

        # Load master image with pyvips
        master_img = pyvips.Image.new_from_file(str(master_path))
        orig_w = master_img.width
        orig_h = master_img.height

        # Calculate working scale
        target_long = float(config.target_long_edge)
        scale = target_long / max(orig_w, orig_h)
        if scale > 1.0:
            scale = 1.0  # Don't upscale small images

        new_w = int(round(orig_w * scale))
        new_h = int(round(orig_h * scale))

        # Downsample using pyvips thumbnail or resize
        if scale < 1.0:
            resized_vips = master_img.resize(scale)
        else:
            resized_vips = master_img

        # Convert to 8-bit sRGB numpy array
        if resized_vips.bands > 3:
            resized_vips = resized_vips.extract_band(0, n=3)
        np_img = resized_vips.numpy()

        # 1. Grayscale
        if len(np_img.shape) == 3 and np_img.shape[2] >= 3:
            gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
        else:
            gray = np_img.copy()

        if gray.dtype != np.uint8:
            gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        # 2. Background Normalization with large Gaussian blur subtraction
        bg_ksize = max(51, int(101 * scale))
        if bg_ksize % 2 == 0:
            bg_ksize += 1
        blurred_bg = cv2.GaussianBlur(gray, (bg_ksize, bg_ksize), 0)
        diff = cv2.subtract(blurred_bg, gray)
        norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

        # 3. Ink Mask: Dual Otsu + Adaptive Thresholding
        _, otsu_mask = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        adapt_mask = cv2.adaptiveThreshold(
            norm, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, -3
        )
        ink_mask = cv2.bitwise_or(otsu_mask, adapt_mask)

        # 4. Noise filtering (remove tiny dust/speckles)
        kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        clean_mask = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN, kernel_clean)

        # 5. Stroke consolidation (connect illustration details without over-bridging)
        conn_ksize = max(7, int(15 * (config.sensitivity / 0.5)))
        kernel_connect = cv2.getStructuringElement(cv2.MORPH_RECT, (conn_ksize, conn_ksize))
        grouped_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel_connect)

        # 6. Connected Components Analysis
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            grouped_mask, connectivity=8
        )

        min_area = int((new_w * new_h) * config.min_area_ratio)
        max_area = int((new_w * new_h) * config.max_area_ratio)
        edge_margin = max(5, int(12 * scale))

        candidate_boxes = []
        for i in range(1, num_labels):
            x, y, w, h, area = stats[i]
            if area < min_area or area > max_area:
                continue

            # Scanner border & Binding suppression
            is_touching_edge = (
                x <= edge_margin
                or y <= edge_margin
                or (x + w) >= new_w - edge_margin
                or (y + h) >= new_h - edge_margin
            )
            if is_touching_edge:
                # If hugging the outer edge and very wide or tall (e.g. spine binding/margin)
                if w > 0.55 * new_w or h > 0.55 * new_h or (w * h) > 0.25 * (new_w * new_h):
                    continue
                if (w / float(h) > 6.0 or h / float(w) > 6.0) and (w > 0.3 * new_w or h > 0.3 * new_h):
                    continue

            # Text suppression heuristic (filter thin horizontal text lines)
            if config.text_suppression:
                aspect_ratio = w / float(h) if h > 0 else 0
                if aspect_ratio > 12.0 and h < int(45 * scale):
                    continue

            # Ink density verification: illustrations have between 0.5% and 85% ink
            box_ink = clean_mask[y:y + h, x:x + w]
            ink_count = np.count_nonzero(box_ink)
            ink_density = ink_count / float(w * h) if (w * h) > 0 else 0
            if ink_density < 0.005 or ink_density > 0.85:
                continue

            candidate_boxes.append([x, y, x + w, y + h, area])

        # 7. Spatial Clustering: Merge overlapping / very close components
        merged_boxes = self._merge_close_boxes(
            candidate_boxes, max_dist=int(config.merge_distance * scale)
        )

        # 8. Convert to Master Coordinates and construct RegionModel list
        regions: List[RegionModel] = []
        for idx, (x1, y1, x2, y2, area) in enumerate(merged_boxes, start=1):
            orig_x = max(0, min(orig_w - 1, int(round(x1 / scale))))
            orig_y = max(0, min(orig_h - 1, int(round(y1 / scale))))
            orig_x2 = max(orig_x + 1, min(orig_w, int(round(x2 / scale))))
            orig_y2 = max(orig_y + 1, min(orig_h, int(round(y2 / scale))))
            orig_width = orig_x2 - orig_x
            orig_height = orig_y2 - orig_y

            box_area = orig_width * orig_height
            confidence = min(0.99, max(0.50, round(0.70 + (box_area / (orig_w * orig_h)) * 0.25, 2)))

            regions.append(
                RegionModel(
                    id=str(uuid.uuid4())[:8],
                    sequence=idx,
                    geometry=RectangleGeometry(
                        x=float(orig_x),
                        y=float(orig_y),
                        width=float(orig_width),
                        height=float(orig_height),
                    ),
                    source="auto",
                    status=RegionStatus.AUTO,
                    name=f"Illustration #{idx}",
                    tags=["auto-detected"],
                    padding=Padding(
                        top=config.padding_default,
                        right=config.padding_default,
                        bottom=config.padding_default,
                        left=config.padding_default,
                    ),
                    export=RegionExportSettings(archive=True, clean=True, vector=False),
                    confidence=confidence,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )

        return regions

    def _merge_close_boxes(self, boxes: List[List[float]], max_dist: int = 25) -> List[List[float]]:
        if not boxes:
            return []

        sorted_boxes = sorted(boxes, key=lambda b: b[4], reverse=True)
        merged: List[List[float]] = []

        for box in sorted_boxes:
            x1, y1, x2, y2, area = box
            merged_into = False

            for i, m in enumerate(merged):
                mx1, my1, mx2, my2, marea = m
                
                # Check enclosure or overlap
                is_enclosed = (x1 >= mx1 and y1 >= my1 and x2 <= mx2 and y2 <= my2) or \
                              (mx1 >= x1 and my1 >= y1 and mx2 <= x2 and my2 <= y2)
                
                # Bounding box distance
                dx = max(0, max(x1, mx1) - min(x2, mx2))
                dy = max(0, max(y1, my1) - min(y2, my2))
                dist = math.hypot(dx, dy)

                if is_enclosed or dist <= max_dist:
                    merged[i] = [
                        min(x1, mx1),
                        min(y1, my1),
                        max(x2, mx2),
                        max(y2, my2),
                        marea + area,
                    ]
                    merged_into = True
                    break

            if not merged_into:
                merged.append([x1, y1, x2, y2, area])

        # Sort top-to-bottom, left-to-right reading order
        return sorted(merged, key=lambda b: (b[1], b[0]))
