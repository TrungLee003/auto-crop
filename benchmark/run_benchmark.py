import csv
import json
import os
import sys
import time
from pathlib import Path
import cv2

# Add root and backend to sys.path
root_path = Path(__file__).resolve().parent.parent
backend_path = root_path / "backend"
sys.path.insert(0, str(root_path))
sys.path.insert(0, str(backend_path))

from app.detection.base import DetectionConfig
from app.detection.opencv import OpenCVDetector
from benchmark.evaluator import evaluate_detections
from benchmark.generate_dataset import build_benchmark_dataset


def run_benchmark():
    benchmark_dir = Path(__file__).resolve().parent
    manifest_file = benchmark_dir / "dataset_manifest.json"

    # 1. Ensure dataset exists
    if not manifest_file.exists():
        print("[Benchmark] Generating synthetic ground truth benchmark dataset...")
        build_benchmark_dataset(benchmark_dir)

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    results_dir = benchmark_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    detector = OpenCVDetector()
    config = DetectionConfig(
        sensitivity=0.65,
        suppress_text=True,
        min_area_px=10000,
    )

    per_page_results = []
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_gt = 0
    total_det = 0
    all_ious = []
    total_time_ms = 0.0

    print("=========================================================================================")
    print("                      HISTORICAL DOCUMENT DETECTION BENCHMARK                            ")
    print("=========================================================================================")
    print(f"{'Page':<20} | {'Category':<12} | {'GT':<4} | {'Det':<4} | {'TP':<4} | {'Recall':<8} | {'Precision':<10} | {'IoU':<6} | {'Time (ms)'}")
    print("-" * 95)

    for item in manifest:
        page_name = item["page"]
        cat_name = item["category"]
        img_path = Path(item["image_path"])
        anno_path = Path(item["annotation_path"])

        with open(anno_path, "r", encoding="utf-8") as f:
            anno_data = json.load(f)
        gt_boxes = anno_data["regions"]

        # Run detection with latency timing
        t0 = time.perf_counter()
        detected_candidates = detector.detect(img_path, config=config)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        total_time_ms += elapsed_ms

        # Convert detected candidates to bounding box format
        det_boxes = []
        for c in detected_candidates:
            det_boxes.append({
                "x": c.geometry.x,
                "y": c.geometry.y,
                "width": c.geometry.width,
                "height": c.geometry.height,
            })

        metrics = evaluate_detections(gt_boxes, det_boxes, iou_threshold=0.40)
        metrics.elapsed_ms = elapsed_ms

        total_tp += metrics.tp
        total_fp += metrics.fp
        total_fn += metrics.fn
        total_gt += metrics.total_gt
        total_det += metrics.total_det
        if metrics.mean_iou > 0:
            all_ious.append(metrics.mean_iou)

        per_page_results.append({
            "page": page_name,
            "category": cat_name,
            "ground_truth": metrics.total_gt,
            "detected": metrics.total_det,
            "tp": metrics.tp,
            "fp": metrics.fp,
            "fn": metrics.fn,
            "recall": f"{metrics.recall * 100:.1f}%",
            "precision": f"{metrics.precision * 100:.1f}%",
            "f1": f"{metrics.f1_score * 100:.1f}%",
            "mean_iou": f"{metrics.mean_iou:.3f}",
            "time_ms": elapsed_ms,
        })

        print(f"{page_name:<20} | {cat_name:<12} | {metrics.total_gt:<4} | {metrics.total_det:<4} | {metrics.tp:<4} | {metrics.recall*100:>6.1f}% | {metrics.precision*100:>8.1f}% | {metrics.mean_iou:>5.3f} | {elapsed_ms:>6.1f} ms")

    # Overall Metrics
    overall_recall = float(total_tp / total_gt) if total_gt > 0 else 0.0
    overall_precision = float(total_tp / total_det) if total_det > 0 else 0.0
    overall_f1 = float(2 * overall_precision * overall_recall / (overall_precision + overall_recall)) if (overall_precision + overall_recall) > 0 else 0.0
    overall_mean_iou = float(sum(all_ious) / len(all_ious)) if all_ious else 0.0
    avg_time_ms = round(total_time_ms / len(manifest), 1)

    print("=" * 95)
    print(f"OVERALL SUMMARY: Recall={overall_recall*100:.1f}% | Precision={overall_precision*100:.1f}% | F1={overall_f1*100:.1f}% | Mean IoU={overall_mean_iou:.3f} | Avg Time={avg_time_ms} ms/page")
    print("=" * 95)

    # 1. Save CSV
    csv_path = results_dir / "benchmark_results.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["page", "category", "ground_truth", "detected", "tp", "fp", "fn", "recall", "precision", "f1", "mean_iou", "time_ms"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(per_page_results)

    # 2. Save Markdown Report
    md_path = results_dir / "benchmark_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Historical Document Detection Benchmark Report\n\n")
        f.write(f"- **Detector**: `OpenCVDetector` (Default)\n")
        f.write(f"- **Pages Evaluated**: {len(manifest)}\n")
        f.write(f"- **Overall Recall**: **{overall_recall*100:.1f}%** (Target ≥ 90%)\n")
        f.write(f"- **Overall Precision**: **{overall_precision*100:.1f}%** (Target ≥ 75%)\n")
        f.write(f"- **Overall F1-Score**: **{overall_f1*100:.1f}%**\n")
        f.write(f"- **Mean IoU**: **{overall_mean_iou:.3f}**\n")
        f.write(f"- **Average Latency**: **{avg_time_ms} ms/page**\n\n")
        f.write("## Per-Category Evaluation Summary\n\n")
        f.write("| Page | Category | Ground Truth | Detected | TP | Recall | Precision | F1 | Mean IoU | Time (ms) |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for r in per_page_results:
            f.write(f"| `{r['page']}` | {r['category']} | {r['ground_truth']} | {r['detected']} | {r['tp']} | {r['recall']} | {r['precision']} | {r['f1']} | {r['mean_iou']} | {r['time_ms']} ms |\n")

    print(f"\n[Benchmark] Results saved to:\n - {csv_path}\n - {md_path}")
    return overall_recall, overall_precision, overall_f1


if __name__ == "__main__":
    run_benchmark()
