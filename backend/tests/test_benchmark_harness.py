import sys
from pathlib import Path
import pytest

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from benchmark.evaluator import calculate_iou, evaluate_detections
from benchmark.generate_dataset import (
    build_benchmark_dataset,
    generate_dense_page,
    generate_sparse_page,
)


def test_iou_calculation():
    box1 = {"x": 0, "y": 0, "width": 100, "height": 100}
    box2 = {"x": 50, "y": 0, "width": 100, "height": 100}
    # Intersection = 50 * 100 = 5000, Union = 10000 + 10000 - 5000 = 15000 -> IoU = 1/3
    iou = calculate_iou(box1, box2)
    assert abs(iou - (1 / 3)) < 1e-4

    # Perfect overlap
    assert calculate_iou(box1, box1) == 1.0

    # No overlap
    box3 = {"x": 200, "y": 200, "width": 50, "height": 50}
    assert calculate_iou(box1, box3) == 0.0


def test_evaluation_metrics():
    gt = [
        {"x": 100, "y": 100, "width": 200, "height": 200},
        {"x": 500, "y": 500, "width": 200, "height": 200},
    ]
    # 1 perfect match, 1 false positive, 1 false negative
    det = [
        {"x": 100, "y": 100, "width": 200, "height": 200},
        {"x": 800, "y": 800, "width": 100, "height": 100},
    ]

    metrics = evaluate_detections(gt, det, iou_threshold=0.5)
    assert metrics.total_gt == 2
    assert metrics.total_det == 2
    assert metrics.tp == 1
    assert metrics.fp == 1
    assert metrics.fn == 1
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1_score == 0.5


def test_dataset_generation(tmp_path):
    manifest = build_benchmark_dataset(tmp_path)
    assert len(manifest) == 10

    pages_dir = tmp_path / "pages"
    anno_dir = tmp_path / "annotations"

    assert len(list(pages_dir.glob("*.png"))) == 10
    assert len(list(anno_dir.glob("*.json"))) == 10
