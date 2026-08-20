# Benchmark Dataset

## Structure

```
benchmark/
├── pages/          # Test page images (minimum 50)
├── annotations/    # Ground truth annotations (manual)
└── README.md
```

## Page Categories (target)

- 10 sparse illustrations
- 10 dense illustrations
- 10 text-heavy pages
- 10 degraded paper
- 10 mixed difficult

## Metrics

- Recall (target ≥ 90%)
- Precision (target ≥ 75%)
- IoU
- Average manual corrections per page (target ≤ 5)
