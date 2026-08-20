# Historical Document Detection Benchmark Report

- **Detector**: `OpenCVDetector` (Default)
- **Pages Evaluated**: 10
- **Overall Recall**: **100.0%** (Target ≥ 90%)
- **Overall Precision**: **100.0%** (Target ≥ 75%)
- **Overall F1-Score**: **100.0%**
- **Mean IoU**: **0.927**
- **Average Latency**: **97.1 ms/page**

## Per-Category Evaluation Summary

| Page | Category | Ground Truth | Detected | TP | Recall | Precision | F1 | Mean IoU | Time (ms) |
|---|---|---|---|---|---|---|---|---|---|
| `sparse_01` | sparse | 2 | 2 | 2 | 100.0% | 100.0% | 100.0% | 0.825 | 100.3 ms |
| `sparse_02` | sparse | 2 | 2 | 2 | 100.0% | 100.0% | 100.0% | 0.825 | 97.7 ms |
| `dense_01` | dense | 5 | 5 | 5 | 100.0% | 100.0% | 100.0% | 0.990 | 99.4 ms |
| `dense_02` | dense | 5 | 5 | 5 | 100.0% | 100.0% | 100.0% | 0.990 | 95.9 ms |
| `text_heavy_01` | text_heavy | 1 | 1 | 1 | 100.0% | 100.0% | 100.0% | 0.971 | 86.8 ms |
| `text_heavy_02` | text_heavy | 1 | 1 | 1 | 100.0% | 100.0% | 100.0% | 0.971 | 98.2 ms |
| `degraded_01` | degraded | 1 | 1 | 1 | 100.0% | 100.0% | 100.0% | 0.993 | 99.0 ms |
| `degraded_02` | degraded | 1 | 1 | 1 | 100.0% | 100.0% | 100.0% | 0.993 | 100.3 ms |
| `mixed_01` | mixed | 2 | 2 | 2 | 100.0% | 100.0% | 100.0% | 0.857 | 98.3 ms |
| `mixed_02` | mixed | 2 | 2 | 2 | 100.0% | 100.0% | 100.0% | 0.857 | 95.3 ms |
