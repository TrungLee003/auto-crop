# Architecture Overview

## System Diagram

```
                         FRONTEND
                            │
                    React + TypeScript
                            │
            ┌───────────────┴───────────────┐
            │                               │
     OpenSeadragon                    Annotorious
      Deep Zoom                      Annotation UI
            │                               │
            └───────────────┬───────────────┘
                            │
                    Custom Tool Layer
            Lasso / Merge / Split / Fit / QA
                            │
                            ▼
                     Annotation Store
                            │
                            ▼
                          FastAPI
                            │
       ┌────────────────────┼─────────────────────┐
       │                    │                     │
       ▼                    ▼                     ▼
     OpenCV               libvips              VTracer
   CV Detection         Image Master          SVG Trace
```

## Image Data Hierarchy

| Level | Path | Purpose | Mutability |
|---|---|---|---|
| SOURCE | `sources/` | Original scan | **Immutable** |
| MASTER | `masters/` | Canonical production image | Created once |
| PYRAMID | `cache/tiles/` | DeepZoom tiles for viewing | Regenerable |
| THUMBNAIL | `cache/thumbnails/` | Page browser previews | Regenerable |

## Coordinate System

All annotations are stored in **MASTER PIXEL COORDINATES**.

```
OpenSeadragon viewport coords  ←→  Coordinate Adapter  ←→  Master Pixels
Annotorious shapes              ←→  Geometry Adapter    ←→  Canonical Geometry
```

Backend never sees OpenSeadragon or DOM coordinates.

## Provider Patterns

### Detection

```
PageService → DetectorRegistry → Detector (ABC)
                                    ├── OpenCVDetector (default)
                                    ├── EynollahDetector (future)
                                    └── DocLayoutYOLODetector (future)
```

### Vectorization

```
VectorService → VectorizerRegistry → Vectorizer (ABC)
                                        ├── VTracerVectorizer (default)
                                        └── PotraceVectorizer (fallback)
```

## Core Invariants

1. SOURCE IS IMMUTABLE
2. MASTER IS CANONICAL
3. TILES ARE VIEW-ONLY
4. ANNOTATION IS THE SOURCE OF TRUTH
5. DETECTION ONLY PROPOSES
6. USER OVERRIDES DETECTOR
7. EXPORT ALWAYS READS MASTER
8. VECTOR EXPORT MUST CONTAIN REAL VECTOR PATHS
