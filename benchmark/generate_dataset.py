import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import cv2
import numpy as np


def generate_sparse_page(width=3000, height=4000) -> Tuple[np.ndarray, List[Dict]]:
    """Category 1: Sparse illustrations on clean background."""
    img = np.full((height, width, 3), 250, dtype=np.uint8)
    gt = []

    # Illustration 1: Woodcut top center
    x1, y1, w1, h1 = 600, 500, 1800, 1200
    cv2.rectangle(img, (x1, y1), (x1 + w1, y1 + h1), (20, 20, 20), 6)
    cv2.circle(img, (x1 + 900, y1 + 600), 400, (30, 30, 30), -1)
    gt.append({"x": x1, "y": y1, "width": w1, "height": h1, "label": "illustration"})

    # Illustration 2: Vignette bottom center
    x2, y2, w2, h2 = 900, 2400, 1200, 900
    cv2.ellipse(img, (x2 + 600, y2 + 450), (500, 350), 0, 0, 360, (25, 25, 25), 5)
    gt.append({"x": x2, "y": y2, "width": w2, "height": h2, "label": "illustration"})

    return img, gt


def generate_dense_page(width=3000, height=4000) -> Tuple[np.ndarray, List[Dict]]:
    """Category 2: Dense multiple small illustrations close together."""
    img = np.full((height, width, 3), 248, dtype=np.uint8)
    gt = []

    positions = [
        (300, 400, 1100, 800),
        (1600, 400, 1100, 800),
        (300, 1500, 1100, 900),
        (1600, 1500, 1100, 900),
        (900, 2700, 1200, 950),
    ]

    for idx, (x, y, w, h) in enumerate(positions, 1):
        cv2.rectangle(img, (x, y), (x + w, y + h), (20, 20, 20), 4)
        for i in range(x + 50, x + w - 50, 40):
            cv2.line(img, (i, y + 50), (i, y + h - 50), (30, 30, 30), 2)
        gt.append({"x": x, "y": y, "width": w, "height": h, "label": f"illustration_{idx}"})

    return img, gt


def generate_text_heavy_page(width=3000, height=4000) -> Tuple[np.ndarray, List[Dict]]:
    """Category 3: Text columns with embedded illustrations (testing text suppression)."""
    img = np.full((height, width, 3), 252, dtype=np.uint8)
    gt = []

    # Draw synthetic text lines (horizontal strokes)
    for y in range(400, 3600, 60):
        # Column 1
        if not (1200 <= y <= 2400):
            cv2.line(img, (300, y), (1350, y), (40, 40, 40), 6)
        # Column 2
        cv2.line(img, (1650, y), (2700, y), (40, 40, 40), 6)

    # Embedded Illustration in Column 1
    x, y, w, h = 300, 1200, 1050, 1200
    cv2.rectangle(img, (x, y), (x + w, y + h), (15, 15, 15), 5)
    cv2.circle(img, (x + 525, y + 600), 300, (20, 20, 20), -1)
    gt.append({"x": x, "y": y, "width": w, "height": h, "label": "embedded_illustration"})

    return img, gt


def generate_degraded_page(width=3000, height=4000) -> Tuple[np.ndarray, List[Dict]]:
    """Category 4: Degraded paper with uneven lighting, stains, and foxing."""
    # Gradient background
    y_grad = np.linspace(190, 245, height).reshape(height, 1)
    x_grad = np.linspace(190, 245, width).reshape(1, width)
    bg = ((y_grad + x_grad) / 2).astype(np.uint8)
    img = cv2.merge([bg, bg, bg])

    # Add simulated foxing stains
    np.random.seed(42)
    for _ in range(30):
        fx = np.random.randint(100, width - 100)
        fy = np.random.randint(100, height - 100)
        fr = np.random.randint(30, 120)
        cv2.circle(img, (fx, fy), fr, (170, 170, 170), -1)

    gt = []
    # Illustration in degraded page
    x, y, w, h = 500, 800, 2000, 2200
    cv2.rectangle(img, (x, y), (x + w, y + h), (10, 10, 10), 6)
    cv2.ellipse(img, (x + 1000, y + 1100), (800, 600), 30, 0, 360, (20, 20, 20), 4)
    gt.append({"x": x, "y": y, "width": w, "height": h, "label": "degraded_illustration"})

    return img, gt


def generate_mixed_page(width=3000, height=4000) -> Tuple[np.ndarray, List[Dict]]:
    """Category 5: Mixed complex geometries and ornate borders."""
    img = np.full((height, width, 3), 245, dtype=np.uint8)
    gt = []

    # Large Ornate Border Illustration
    x1, y1, w1, h1 = 300, 400, 2400, 1600
    cv2.rectangle(img, (x1, y1), (x1 + w1, y1 + h1), (20, 20, 20), 8)
    cv2.rectangle(img, (x1 + 60, y1 + 60), (x1 + w1 - 60, y1 + h1 - 60), (20, 20, 20), 3)
    gt.append({"x": x1, "y": y1, "width": w1, "height": h1, "label": "ornate_headpiece"})

    # Lower circular medallion
    x2, y2, w2, h2 = 800, 2400, 1400, 1200
    cv2.ellipse(img, (x2 + 700, y2 + 600), (600, 500), 0, 0, 360, (15, 15, 15), 5)
    gt.append({"x": x2, "y": y2, "width": w2, "height": h2, "label": "medallion"})

    return img, gt


def build_benchmark_dataset(output_dir: Path):
    """Generates benchmark dataset across all 5 historical categories."""
    pages_dir = output_dir / "pages"
    annotations_dir = output_dir / "annotations"
    pages_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)

    categories = [
        ("sparse", generate_sparse_page, 2),
        ("dense", generate_dense_page, 2),
        ("text_heavy", generate_text_heavy_page, 2),
        ("degraded", generate_degraded_page, 2),
        ("mixed", generate_mixed_page, 2),
    ]

    manifest = []

    for cat_name, gen_func, count in categories:
        for i in range(1, count + 1):
            page_name = f"{cat_name}_{i:02d}"
            img, gt = gen_func()

            img_file = pages_dir / f"{page_name}.png"
            json_file = annotations_dir / f"{page_name}.json"

            cv2.imwrite(str(img_file), img)
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump({
                    "page": page_name,
                    "width": img.shape[1],
                    "height": img.shape[0],
                    "category": cat_name,
                    "regions": gt
                }, f, indent=2)

            manifest.append({
                "page": page_name,
                "category": cat_name,
                "image_path": str(img_file),
                "annotation_path": str(json_file),
                "ground_truth_count": len(gt),
            })

    # Save manifest
    with open(output_dir / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


if __name__ == "__main__":
    benchmark_dir = Path(__file__).resolve().parent
    build_benchmark_dataset(benchmark_dir)
    print("Benchmark dataset generated successfully.")
