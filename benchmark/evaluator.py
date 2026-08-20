from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


def calculate_iou(box_a: Dict[str, float], box_b: Dict[str, float]) -> float:
    """
    Computes Intersection over Union (IoU) between two bounding boxes.
    Boxes are expected to have keys: 'x', 'y', 'width', 'height' (or 'min_x', 'min_y', etc.)
    """
    ax1 = box_a.get("x", box_a.get("min_x", 0))
    ay1 = box_a.get("y", box_a.get("min_y", 0))
    ax2 = ax1 + box_a.get("width", 0)
    ay2 = ay1 + box_a.get("height", 0)

    bx1 = box_b.get("x", box_b.get("min_x", 0))
    by1 = box_b.get("y", box_b.get("min_y", 0))
    bx2 = bx1 + box_b.get("width", 0)
    by2 = by1 + box_b.get("height", 0)

    # Intersection rectangle
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    inter_w = max(0.0, ix2 - ix1)
    inter_h = max(0.0, iy2 - iy1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(0.0, (bx2 - bx1) * (by2 - by1))
    union_area = area_a + area_b - inter_area

    if union_area <= 0:
        return 0.0

    return float(inter_area / union_area)


@dataclass
class EvaluationMetrics:
    total_gt: int
    total_det: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1_score: float
    mean_iou: float
    elapsed_ms: float = 0.0


def evaluate_detections(
    ground_truth_list: List[Dict[str, float]],
    detected_list: List[Dict[str, float]],
    iou_threshold: float = 0.40
) -> EvaluationMetrics:
    """
    Evaluates detector output against ground-truth boxes using bipartite matching.
    """
    gt_matched = set()
    det_matched = set()
    matched_ious = []

    # Greedy match by highest IoU
    candidates = []
    for gt_idx, gt_box in enumerate(ground_truth_list):
        for det_idx, det_box in enumerate(detected_list):
            iou = calculate_iou(gt_box, det_box)
            if iou >= iou_threshold:
                candidates.append((iou, gt_idx, det_idx))

    # Sort descending by IoU
    candidates.sort(key=lambda x: x[0], reverse=True)

    for iou, gt_idx, det_idx in candidates:
        if gt_idx not in gt_matched and det_idx not in det_matched:
            gt_matched.add(gt_idx)
            det_matched.add(det_idx)
            matched_ious.append(iou)

    tp = len(gt_matched)
    fp = len(detected_list) - len(det_matched)
    fn = len(ground_truth_list) - len(gt_matched)

    total_gt = len(ground_truth_list)
    total_det = len(detected_list)

    precision = float(tp / total_det) if total_det > 0 else 0.0
    recall = float(tp / total_gt) if total_gt > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    mean_iou = float(sum(matched_ious) / len(matched_ious)) if matched_ious else 0.0

    return EvaluationMetrics(
        total_gt=total_gt,
        total_det=total_det,
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1_score=f1,
        mean_iou=mean_iou
    )
