# Illustration Extractor
## Dev-Ready Product & Technical Plan — V2

**Status:** Development baseline  
**Version:** 2.0  
**Supersedes:** V1 specification  
**Architecture:** Local-first / semi-automatic / non-destructive  
**Primary target:** Windows 10/11 x64  
**Primary use case:** Tách hàng loạt các hình minh họa riêng lẻ từ sách, tài liệu, atlas và bản scan lịch sử có nhiều hình trên cùng một trang.

---

# 0. Executive Summary

Illustration Extractor là công cụ:

```text
SOURCE SCANS
     ↓
PAGE ANALYSIS
     ↓
AUTO-DETECT ILLUSTRATIONS
     ↓
HIGH-RES INTERACTIVE REVIEW
     ↓
USER EDITS REGIONS
     ↓
APPROVAL
     ↓
HIGH-RES RASTER / CLEAN PNG / VECTOR SVG
```

Triết lý sản phẩm:

> Automation proposes. Human approves.

Hệ thống không cố đạt 100% automatic segmentation.

Mục tiêu thực tế:

1. máy tự phát hiện phần lớn hình;
2. người dùng sửa nhanh các vùng sai;
3. tất cả thao tác là non-destructive;
4. export luôn lấy từ master resolution;
5. hỗ trợ scan rất lớn;
6. line-art có thể vector hóa để scale không phụ thuộc resolution.

---

# 1. Architectural Changes From V1

## V1

```text
React
+
Konva

FastAPI
+
OpenCV
+
pyvips
+
Potrace
```

## V2

```text
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
       │                    │
       │                    ├── TIFF
       │                    ├── PNG
       │                    ├── high-res crop
       │                    ├── image pyramid
       │                    └── DeepZoom
       │
       ▼
 Detector Provider
 ├── OpenCVDetector            DEFAULT
 ├── EynollahDetector          EXPERIMENTAL
 ├── DocLayoutYOLODetector     FUTURE
 └── SAM2InteractiveDetector   FUTURE
```

---

# 2. Reference Repositories

Các repo sau được dùng như **engineering references**, không phải source base để fork toàn bộ.

| Repo | Vai trò |
|---|---|
| `annotorious/annotorious` | Annotation primitives và editor architecture |
| `openseadragon/openseadragon` | High-resolution tiled viewer |
| `libvips/libvips` | High-resolution image processing |
| `libvips/pyvips` | Python binding cho libvips |
| `visioncortex/vtracer` | Raster → vector SVG |
| `ScanTailor-Advanced/scantailor-advanced` | Workflow xử lý scan |
| `wkentaro/labelme` | Manual annotation UX |
| `cvat-ai/cvat` | Review/job/state architecture |
| `qurator-spk/eynollah` | Historical document analysis |
| `Layout-Parser/layout-parser` | Detector abstraction |
| `opendatalab/DocLayout-YOLO` | Future document layout detector |
| `facebookresearch/sam2` | Future interactive segmentation |

Annotorious hiện có implementation cho polygon, multipolygon, polygon editor, rotated rectangle và OpenSeadragon integration, vì vậy V2 không tự xây toàn bộ annotation engine từ đầu.   

OpenSeadragon được thiết kế riêng cho zoomable images, phù hợp với scan 600–1200 DPI và image pyramid. 

libvips sử dụng demand-driven processing, có memory footprint thấp và hỗ trợ TIFF, PNG, DeepZoom cùng nhiều định dạng ảnh lớn. 

VTracer hỗ trợ B/W line-art, adaptive threshold và được thiết kế để xử lý cả high-resolution historical scans; vì vậy được chọn làm vectorizer mặc định của V2. 

---

# 3. Product Goals

## G1 — Batch first

Tool phải xử lý được:

```text
1 image
10 images
100 images
1,000+ images
```

mà workflow không thay đổi.

---

## G2 — Human-correctable

Mọi kết quả automatic detection phải:

```text
editable
movable
resizable
deletable
mergeable
splittable
approvable
```

---

## G3 — Resolution preservation

Canvas/editor resolution không quyết định export resolution.

Invariant:

```text
EDITOR → ANNOTATION
ANNOTATION + MASTER → EXPORT
```

Không được:

```text
EDITOR SCREENSHOT → EXPORT
```

---

## G4 — Historical document friendly

Phải hoạt động tốt với:

- giấy vàng;
- foxing;
- stains;
- faded ink;
- fine line art;
- handwritten annotations;
- Hán/Nôm;
- vertical text;
- multiple illustrations không theo grid;
- trang không có layout hiện đại.

---

## G5 — Local-first

Core application:

```text
NO CLOUD REQUIRED
NO ACCOUNT REQUIRED
NO IMAGE UPLOAD
NO INTERNET REQUIRED
```

---

# 4. Non-Goals

V1/V2 production baseline không phải:

- OCR application;
- digital archive DAM;
- PDF editor;
- Photoshop replacement;
- training-data labeling platform;
- collaborative cloud service;
- generative restoration tool.

---

# 5. Core Workflow

```text
CREATE PROJECT
       ↓
IMPORT SCANS
       ↓
GENERATE PREVIEWS + DEEPZOOM PYRAMIDS
       ↓
AUTO DETECT
       ↓
PAGE STATUS = DETECTED
       ↓
OPEN REVIEW MODE
       ↓
EDIT REGIONS
       ↓
APPROVE PAGE
       ↓
PAGE STATUS = REVIEWED
       ↓
EXPORT
       ↓
ARCHIVE / DESIGN / VECTOR
```

---

# 6. Image Data Hierarchy

Phải tách rõ 4 cấp.

## 6.1 SOURCE

Scan gốc.

Immutable.

```text
sources/
```

Không được overwrite trong bất kỳ trường hợp nào.

---

## 6.2 MASTER

Canonical production image.

```text
masters/
```

Nếu không preprocessing:

```text
MASTER = SOURCE
```

Nếu có:

- deskew;
- rotate;
- page crop;
- dewarp;

thì tạo master mới.

---

## 6.3 PYRAMID

DeepZoom/tiled representation.

```text
cache/tiles/
```

Sinh từ MASTER bằng libvips.

Chỉ dùng viewing.

---

## 6.4 THUMBNAIL

Dùng cho page browser.

```text
cache/thumbnails/
```

---

# 7. Canonical Coordinate System

Toàn bộ annotation phải lưu theo:

```text
MASTER PIXEL COORDINATES
```

Không dùng:

- DOM coordinates;
- viewport coordinates;
- screen coordinates;
- OpenSeadragon viewport coordinates;
- thumbnail coordinates.

Ví dụ master:

```text
Width  = 12000
Height = 8000
```

Polygon:

```json
[
  [3312, 1704],
  [4480, 1658],
  [4612, 2864],
  [3401, 2940]
]
```

OpenSeadragon coordinates chỉ là projection.

---

# 8. Core Invariants

Developer không được phá các invariant sau:

```text
SOURCE IS IMMUTABLE

MASTER IS CANONICAL

TILES ARE VIEW-ONLY

ANNOTATION IS THE SOURCE OF TRUTH

DETECTION ONLY PROPOSES

USER OVERRIDES DETECTOR

EXPORT ALWAYS READS MASTER

VECTOR EXPORT MUST CONTAIN REAL VECTOR PATHS
```

---

# 9. Tech Stack

## Frontend

```text
React
TypeScript
Vite
OpenSeadragon
Annotorious
Zustand
TanStack Query
```

Optional:

```text
Radix UI
Tailwind CSS
```

---

## Backend

```text
Python 3.11+
FastAPI
Pydantic v2
OpenCV
NumPy
pyvips
Shapely
scikit-image
```

Optional:

```text
SciPy
```

---

## Vector

Default:

```text
VTracer
```

Fallback:

```text
Potrace
```

---

## Desktop

Preferred:

```text
Electron
```

Backend packaging:

```text
PyInstaller
```

Alternative future:

```text
Tauri
```

không đưa vào V1.

---

# 10. Why OpenSeadragon

Không load ảnh 100 MP trực tiếp vào canvas.

Thay vào đó:

```text
MASTER
  ↓
libvips dzsave
  ↓
DeepZoom pyramid
  ↓
OpenSeadragon
```

Ví dụ:

```text
12000 × 8000
6000 × 4000
3000 × 2000
1500 × 1000
...
```

OpenSeadragon chỉ fetch tile cần thiết cho viewport hiện tại.

---

# 11. Why Annotorious

Annotorious chịu trách nhiệm:

- selection;
- rectangle;
- polygon;
- annotation event;
- geometry rendering;
- geometry editing;
- rotated rectangle where usable.

Custom layer chỉ bổ sung những workflow riêng của Illustration Extractor.

Không fork toàn bộ Annotorious nếu không cần.

---

# 12. Custom Annotation Tools

Phải viết thêm:

```text
Lasso
Fit to Content
Merge
Split
Padding
Approve / Reject
Region Metadata
Region Export Preview
```

---

# 13. Region Geometry Types

Canonical schema hỗ trợ:

```text
RECTANGLE
ROTATED_RECTANGLE
POLYGON
MULTIPOLYGON
```

Lasso cuối cùng cũng convert thành:

```text
POLYGON
```

Không lưu raw mouse trace lâu dài.

---

# 14. Rectangle

Schema:

```json
{
  "type": "rectangle",
  "x": 120,
  "y": 400,
  "width": 720,
  "height": 460
}
```

---

# 15. Rotated Rectangle

```json
{
  "type": "rotated_rectangle",
  "cx": 1600,
  "cy": 2400,
  "width": 1100,
  "height": 720,
  "angle": 13.5
}
```

---

# 16. Polygon

```json
{
  "type": "polygon",
  "points": [
    [120, 300],
    [980, 280],
    [1050, 760],
    [690, 1030],
    [190, 850]
  ]
}
```

Must support:

```text
concave
arbitrary vertices
self-intersection validation
```

---

# 17. MultiPolygon

Một illustration có thể gồm hai khu vực không nối nhau.

Ví dụ:

```text
main illustration
+
separate caption symbol
```

nếu user chủ động muốn group.

Schema:

```json
{
  "type": "multipolygon",
  "polygons": [...]
}
```

---

# 18. Lasso

Workflow:

```text
Pointer samples
↓
Raw path
↓
Close shape
↓
Ramer–Douglas–Peucker
↓
Self-intersection check
↓
Polygon
↓
Editable vertices
```

Expose:

```text
simplification tolerance
```

---

# 19. Region Model

```json
{
  "id": "uuid",
  "sequence": 17,

  "geometry": {},

  "source": "auto",

  "status": "edited",

  "name": null,

  "tags": [],

  "padding": {
    "top": 40,
    "right": 40,
    "bottom": 40,
    "left": 40
  },

  "export": {
    "archive": true,
    "clean": true,
    "vector": false
  },

  "created_at": "...",
  "updated_at": "..."
}
```

---

# 20. Region Lifecycle

```text
AUTO
 ↓
EDITED
 ↓
APPROVED
```

Alternative:

```text
AUTO
 ↓
REJECTED
```

Không delete region auto ngay khi reject.

Giữ trong annotation history.

---

# 21. Page Lifecycle

Dựa theo review workflow kiểu CVAT nhưng đơn giản hóa:

```text
NEW
 ↓
PROCESSING
 ↓
DETECTED
 ↓
IN_REVIEW
 ↓
REVIEWED
 ↓
EXPORTED
```

Error:

```text
FAILED
```

CVAT là reference phù hợp cho task/job/review state machine, nhưng chúng ta không mang theo collaboration stack hay dataset features của họ. 

---

# 22. Project Model

```json
{
  "schema_version": 2,

  "project_id": "uuid",

  "name": "Historical Book",

  "created_at": "...",
  "updated_at": "...",

  "settings": {},

  "pages": []
}
```

---

# 23. Project Folder

```text
project/
│
├── project.json
│
├── sources/
│
├── masters/
│
├── annotations/
│
├── cache/
│   ├── thumbnails/
│   ├── deepzoom/
│   ├── masks/
│   └── detection/
│
├── exports/
│   ├── archive/
│   ├── clean/
│   └── vector/
│
└── logs/
```

---

# 24. Portability

Project dùng relative paths.

Sai:

```text
D:\User\Book\page001.tif
```

Đúng:

```text
sources/page001.tif
```

Copy project folder sang máy khác phải mở được.

---

# 25. Import

Support:

```text
JPEG
PNG
TIFF
WebP
```

Optional later:

```text
JPEG2000
PDF raster pages
```

---

# 26. Import Modes

## COPY

Default.

```text
external scan
→
project/sources
```

## REFERENCE

Advanced.

Project tham chiếu external file.

UI warning khi source unavailable.

---

# 27. Duplicate Detection

Use:

```text
file size
+
fast hash
```

Optional full:

```text
SHA-256
```

Không import duplicate mặc định.

---

# 28. Image Core

libvips là default cho:

```text
read large images
write large images
crop
resize
TIFF
PNG
DeepZoom
metadata
ICC
```

OpenCV không được dùng làm high-resolution archive writer nếu libvips xử lý được.

---

# 29. Color & Metadata

Archive mode cố giữ:

```text
ICC profile
DPI
bit depth
orientation information
```

Không silent convert:

```text
16-bit → 8-bit
```

nếu không cần.

---

# 30. Preview Generation

Thumbnail:

```text
256–400 px
```

DeepZoom:

```text
MASTER
→
libvips dzsave
```

Output example:

```text
page-014.dzi
page-014_files/
├── 0/
├── 1/
├── ...
└── 13/
```

---

# 31. Detection Architecture

Không viết một `detect.py` monolithic.

Interface:

```python
class Detector:
    def detect(
        self,
        image_ref: ImageReference,
        settings: DetectionSettings
    ) -> list[RegionCandidate]:
        ...
```

Implement:

```text
OpenCVDetector
EynollahDetector
DocLayoutYOLODetector
```

---

# 32. Default Detector — OpenCV

V2 vẫn giữ OpenCV làm default vì:

- không cần model;
- CPU friendly;
- offline;
- fast;
- deterministic;
- dễ tune;
- hợp trang sparse line-art.

---

# 33. OpenCV Detection Pipeline

```text
MASTER
 ↓
Detection working image
 ↓
Background normalization
 ↓
Grayscale
 ↓
Ink mask
 ↓
Noise filtering
 ↓
Connected components
 ↓
Component graph
 ↓
Spatial clustering
 ↓
Candidate groups
 ↓
Region generation
 ↓
Candidate filtering
```

---

# 34. Detection Resolution

Không chạy OpenCV ở full 1200 DPI nếu không cần.

Default:

```text
working long edge = 3500 px
```

Range:

```text
2500–5000 px
```

Sau detection:

```text
working coords
→
master coords
```

---

# 35. Historical Paper Normalization

Recommended:

```text
gray
↓
large-radius background estimate
↓
local normalization
↓
ink isolation
```

Methods:

```text
Gaussian background
Morphological opening
CLAHE optional
```

Không normalize source/master.

Chỉ working copy.

---

# 36. Ink Mask

Methods:

```text
Adaptive threshold
Otsu
Manual
```

Default:

```text
Adaptive
```

---

# 37. Component Filtering

Connected component metadata:

```text
bbox
area
centroid
density
aspect ratio
stroke proxy
```

Filter:

```text
paper speckle
isolated dust
page border
scan edge
```

---

# 38. Spatial Clustering

Một illustration ≠ một connected component.

Build graph:

```text
component = node
potential spatial relation = edge
```

Merge based on:

```text
edge distance
centroid distance
horizontal overlap
vertical overlap
relative scale
local density
```

Then:

```text
connected graph components
→
illustration candidates
```

---

# 39. Multi-scale Grouping

Run clustering ít nhất hai scale:

```text
tight
normal
```

Optional:

```text
loose
```

Reconcile candidates bằng:

```text
IoU
containment
group score
```

---

# 40. Text Handling

Modes:

```text
KEEP_ALL
PREFER_ART
ART_ONLY_EXPERIMENTAL
```

Default:

```text
PREFER_ART
```

Không dùng OCR làm dependency.

Hán/Nôm hoặc handwritten captions không được coi là reliably removable text.

---

# 41. Detection Confidence

Mỗi candidate nên có:

```json
{
  "score": 0.82,
  "signals": {
    "area": 0.91,
    "density": 0.74,
    "separation": 0.79
  }
}
```

UI có thể hiển thị confidence thấp khác màu.

---

# 42. Future Historical Detector — Eynollah

Eynollah được phát triển cho historical document layout và hỗ trợ image region, page border, text region, separator, marginalia cùng binarization. 

Không bật mặc định.

Implement sau khi benchmark OpenCV.

Integration:

```text
Eynollah output
↓
Image Regions
↓
RegionCandidate adapter
```

---

# 43. Future DocLayout-YOLO

DocLayout-YOLO được giữ như optional AI detector cho trang có layout phức tạp hơn. Repo hỗ trợ pretrained model và inference pipeline. 

Không dependency V1.

---

# 44. Future SAM2

SAM2 không dùng để auto-detect toàn trang trong baseline.

Use case tương lai:

```text
User click illustration
↓
SAM2 mask
↓
mask → polygon
↓
user adjusts
```

SAM2 hỗ trợ promptable segmentation và automatic mask generation, nên phù hợp cho interactive refine về sau. 

---

# 45. Main UI

```text
┌──────────────────────────────────────────────────────────┐
│ Menu / Project / Detect / Export                         │
├─────────────┬───────────────────────────┬────────────────┤
│ PAGE LIST   │                           │ REGION PANEL   │
│             │                           │                │
│ thumbnails  │     OPEN SEADRAGON        │ Geometry       │
│ status      │        VIEWER             │ Padding        │
│ filters     │                           │ Status         │
│             │     + ANNOTORIOUS         │ Export         │
│             │       OVERLAY             │ Metadata       │
│             │                           │                │
├─────────────┴───────────────────────────┴────────────────┤
│ Zoom | Coordinates | Master size | Save | Job progress  │
└──────────────────────────────────────────────────────────┘
```

---

# 46. Page Sidebar

Each row:

```text
thumbnail
filename
region count
status
warning indicator
```

Filters:

```text
All
New
Detected
Needs Review
Reviewed
Exported
Failed
```

---

# 47. High-resolution Viewer

OpenSeadragon handles:

```text
pan
zoom
deep zoom
tile loading
viewport transforms
```

Application layer handles:

```text
annotation interaction
page state
shortcuts
region selection
```

---

# 48. Zoom Behaviour

Minimum:

```text
Fit Page
Fit Width
100% source approximation
Custom zoom
```

Status bar phải cho thấy:

```text
Viewport zoom
Source pixel scale
```

---

# 49. Annotation Overlay

Annotorious rendered over OpenSeadragon.

Need adapter:

```text
OpenSeadragon viewport coordinates
↔
MASTER pixels
```

Round-trip coordinate tests là release blocker.

---

# 50. Selection Tools

Toolbar:

```text
V Select
R Rectangle
T Rotated Rectangle
P Polygon
L Lasso
F Fit
M Merge
S Split
Delete
```

---

# 51. Fit to Content

Một productivity feature quan trọng.

Input:

```text
current region
+
local ink mask
```

Algorithm:

```text
expand current region slightly
↓
extract working mask
↓
find connected foreground
↓
discard outside clusters
↓
tight bounds / contour
↓
padding
```

Modes:

```text
Fit Rectangle
Fit Polygon
```

---

# 52. Padding

Padding là export property, không nhất thiết phải biến geometry.

```json
{
  "top": 40,
  "right": 40,
  "bottom": 40,
  "left": 40
}
```

Presets:

```text
0
20
40
80
Custom
```

---

# 53. Merge

Select multiple regions.

Modes:

```text
Bounding rectangle
Convex hull
Polygon union
MultiPolygon
```

Default:

```text
Polygon union
```

---

# 54. Split

V1 implementation không cần computational geometry phức tạp.

Preferred:

```text
draw split line
→
attempt polygon split
```

Fallback:

```text
Duplicate
→
edit polygon A
→
edit polygon B
```

Split failure không được crash editor.

---

# 55. Undo / Redo

Minimum:

```text
100 operations
```

Actions:

- create;
- delete;
- reject;
- move;
- resize;
- rotate;
- add point;
- remove point;
- lasso;
- merge;
- split;
- fit;
- padding.

---

# 56. Autosave

Annotation save:

```text
500–1000ms debounce
```

State:

```text
Saved
Saving
Save Failed
```

Write strategy:

```text
temp file
→
fsync
→
atomic replace
```

---

# 57. Keyboard-first Review

```text
V             Select
R             Rectangle
P             Polygon
L             Lasso

Delete        Reject/Delete
F             Fit
M             Merge

Enter         Approve region
Ctrl+Enter    Approve page

Ctrl+Z        Undo
Ctrl+Shift+Z  Redo

Arrow         Nudge 1 px
Shift+Arrow   Nudge 10 px

PageUp        Previous page
PageDown      Next page

0             Fit Page
1             Source-scale view
```

---

# 58. Review Mode

Dedicated mode:

```text
REVIEW
```

Rules:

- auto-focus first unreviewed page;
- auto-select suspicious region;
- keyboard navigation prioritized;
- next unreviewed page after approval;
- no destructive confirmation for simple reject;
- undo available.

---

# 59. Automatic Quality Flags

Page warning if:

```text
0 detected regions
too many regions
region overlaps page border
very small region
region outside bounds
self-intersecting polygon
unapproved regions remain
```

---

# 60. Export Architecture

Frontend never writes production raster.

Flow:

```text
Frontend
↓
annotation IDs + preset
↓
FastAPI
↓
read MASTER using pyvips
↓
apply geometry
↓
output
```

---

# 61. Export Region Bounding

Rectangle:

```text
direct crop
```

Rotated rectangle:

```text
calculate enclosing area
↓
crop
↓
rotate/correct
↓
trim
```

Polygon:

```text
bounding rectangle
↓
crop
↓
high-resolution polygon mask
↓
alpha composite
```

---

# 62. Anti-aliased Polygon Mask

Do not use crude binary edge.

Use:

```text
supersampling
```

Default:

```text
4× mask
↓
downsample
```

or high-quality vector rasterization.

---

# 63. Export Preset — Archive

```yaml
name: archive

format: TIFF

source: master

background: original

cleanup: false

scale: 1

compression: lossless

preserve:
  dpi: true
  icc: true
  bit_depth: true
```

Fallback:

```text
PNG
```

---

# 64. Export Preset — Design Asset

```yaml
name: design

format: PNG

background: transparent

normalize_background: true

despeckle: light

line_enhancement: light

scale: 1
```

Optional:

```text
2×
4×
```

---

# 65. Export Preset — Vector

```yaml
name: vector

format: SVG

normalize_background: true

binarize: adaptive

despeckle: true

vectorizer: vtracer

preset: bw

simplify: conservative
```

---

# 66. Upscaling

Raster modes:

```text
1×
2×
4×
Custom
```

Default interpolation:

```text
Lanczos
```

UI warning:

> Upscaling increases output dimensions but does not create original source detail.

Không gọi đây là "enhance resolution".

---

# 67. Vectorization Engine — VTracer

Default configuration cho historical line-art:

```text
preset = bw
adaptive = true
clustering = bw
simplify = conservative
```

VTracer có adaptive threshold, B/W tracing, curve simplification và high-resolution scan support, phù hợp hơn Potrace làm default. 

---

# 68. Potrace Fallback

Giữ interface:

```python
class Vectorizer:
    def vectorize(
        self,
        raster_path,
        settings
    ) -> VectorResult:
        ...
```

Implement:

```text
VTracerVectorizer
PotraceVectorizer
```

UI default:

```text
VTracer
```

---

# 69. SVG Validation

Export test phải verify:

```text
valid XML
SVG root
viewBox exists
vector paths exist
no raster-only <image> result
```

---

# 70. Before / After Vector Preview

Vector tab nên có:

```text
ORIGINAL
TRACE
```

Toggle:

```text
A / B
```

Future:

```text
split-view
```

Ý tưởng này tương đồng với A/B comparison trong VTracer desktop workflow. 

---

# 71. Scan Preprocessing

Không trộn với annotation step.

Optional preprocess page:

```text
Rotate
Deskew
Crop Page
Background Normalize
```

Future:

```text
Dewarp
```

ScanTailor Advanced là reference cho tư duy:

```text
raw scan
→
page correction
→
content selection
→
manual adjustment
→
output
```

và có các chức năng content detection, picture zones, adaptive binarization và batch processing. 

---

# 72. Preprocessing Order

Nếu user cần geometric correction:

```text
IMPORT
↓
ROTATE
↓
DESKEW
↓
PAGE CROP
↓
MASTER GENERATED
↓
DETECT
↓
ANNOTATE
```

Không rotate/master-transform sau khi annotation trừ khi transform toàn bộ region coordinates chính xác.

---

# 73. Job System

Job types:

```text
IMPORT
MASTER_BUILD
THUMBNAIL
DEEPZOOM
DETECTION
EXPORT_RASTER
VECTORIZE
```

States:

```text
QUEUED
RUNNING
DONE
FAILED
CANCELLED
```

---

# 74. Worker Architecture

Backend process:

```text
FastAPI
+
Job Manager
+
Worker Pool
```

Default workers:

```python
min(max(cpu_count - 1, 1), 4)
```

Heavy jobs như TIFF export phải có concurrency limit riêng.

---

# 75. UI Must Never Freeze

Operations >100 ms phải async/background nếu có khả năng scale.

Ví dụ:

```text
import 500 pages
generate pyramids
detect all
export all
vectorize all
```

---

# 76. Batch Progress

Example:

```text
Detecting pages

147 / 500
29%

Active: page-0147.tif
Failures: 2
```

Failure không stop batch mặc định.

---

# 77. Backend API

Base:

```text
/api/v2
```

---

# 78. Projects

```http
POST   /projects
GET    /projects/{project_id}
PATCH  /projects/{project_id}
DELETE /projects/{project_id}
```

---

# 79. Import

```http
POST /projects/{project_id}/imports
```

Response:

```json
{
  "job_id": "uuid"
}
```

---

# 80. Pages

```http
GET   /projects/{project_id}/pages
GET   /pages/{page_id}
PATCH /pages/{page_id}
```

---

# 81. Tile Metadata

```http
GET /pages/{page_id}/viewer
```

Response:

```json
{
  "master_width": 12000,
  "master_height": 8000,
  "dzi_url": "/tiles/page-id/page.dzi"
}
```

---

# 82. Detection

```http
POST /pages/{page_id}/detect
POST /projects/{project_id}/detect
```

Request:

```json
{
  "provider": "opencv",
  "profile": "historical_line_art"
}
```

---

# 83. Regions

```http
GET /pages/{page_id}/regions
PUT /pages/{page_id}/regions
```

Prefer bulk-save page annotation thay vì request từng vertex movement.

---

# 84. Fit

```http
POST /pages/{page_id}/regions/{region_id}/fit
```

---

# 85. Export

```http
POST /exports
```

Example:

```json
{
  "project_id": "...",
  "scope": "reviewed",
  "preset": "archive"
}
```

Response:

```json
{
  "job_id": "uuid"
}
```

---

# 86. Jobs

```http
GET  /jobs/{job_id}
POST /jobs/{job_id}/cancel
```

---

# 87. Project Settings

Main user-facing controls:

## Detection

```text
Sensitivity
Separation
Minimum object size
Text handling
```

## Editor

```text
Default padding
Polygon simplification
Autosave
Snap
```

## Export

```text
Archive format
Transparent mode
Scale
Naming
```

## Vector

```text
Threshold
Adaptive
Speckle removal
Simplification
```

---

# 88. Advanced Detection Settings

Internal profile maps simplified controls → parameters.

Example:

```yaml
historical_line_art:

  working_long_edge: 3500

  threshold:
    method: adaptive
    block_size: 51
    c: 12

  component:
    min_area_ratio: 0.000002

  grouping:
    tight_distance_ratio: 0.008
    normal_distance_ratio: 0.015

  region:
    min_area_ratio: 0.0005

  text:
    mode: prefer_art
```

---

# 89. Detection Profiles

Built-in:

```text
Historical Line Art
Dense Historical Page
Technical Drawing
Sparse Illustration Page
Custom
```

---

# 90. CLI

```bash
illustration-extractor serve
```

Create:

```bash
illustration-extractor project new ./project
```

Import:

```bash
illustration-extractor import ./project ./scans
```

Detect:

```bash
illustration-extractor detect ./project
```

Export:

```bash
illustration-extractor export ./project --preset archive
```

Vector:

```bash
illustration-extractor export ./project --preset vector
```

---

# 91. Logging

```text
logs/app.log
```

Fields:

```text
timestamp
level
module
project_id
page_id
job_id
message
exception
```

Do not log image pixels.

---

# 92. Recovery

Autosaved page annotation:

```text
annotation.json.tmp
↓
atomic replace
↓
annotation.json
```

Backup:

```text
annotation.json.bak
```

---

# 93. Cache Invalidation

Cache key:

```text
master hash
+
processing settings hash
+
cache version
```

If MASTER changes:

```text
invalidate
thumbnail
deepzoom
detection mask
detection result
```

---

# 94. Repository Structure

```text
illustration-extractor/
│
├── apps/
│   ├── desktop/
│   └── web/
│
├── frontend/
│   ├── src/
│   │   ├── viewer/
│   │   ├── annotation/
│   │   ├── review/
│   │   ├── pages/
│   │   ├── project/
│   │   ├── export/
│   │   ├── jobs/
│   │   ├── stores/
│   │   └── api/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── project/
│   │   ├── images/
│   │   ├── tiles/
│   │   ├── detection/
│   │   │   ├── base.py
│   │   │   ├── opencv.py
│   │   │   └── providers/
│   │   ├── annotation/
│   │   ├── geometry/
│   │   ├── export/
│   │   ├── vector/
│   │   └── jobs/
│   │
│   └── tests/
│
├── samples/
│
├── benchmark/
│   ├── pages/
│   └── annotations/
│
├── docs/
│
└── scripts/
```

---

# 95. Frontend Architectural Rule

Do not couple:

```text
Annotorious geometry
```

directly with:

```text
backend schema
```

Use adapter:

```text
Annotorious Shape
     ↓
Geometry Adapter
     ↓
Canonical Geometry
```

Điều này tránh lock-in.

---

# 96. Viewer Architectural Rule

Tương tự:

```text
OpenSeadragon coordinates
     ↓
Coordinate Adapter
     ↓
Master Pixels
```

Backend không được biết OpenSeadragon coordinates.

---

# 97. Detector Architectural Rule

Không để page service gọi trực tiếp OpenCV functions.

Đúng:

```text
PageService
↓
DetectorRegistry
↓
Detector
```

Future provider plug-in không phải sửa core.

LayoutParser là reference tốt cho kiểu unified detection API này. 

---

# 98. Vector Architectural Rule

Không gọi CLI VTracer trực tiếp khắp code.

Đúng:

```text
VectorService
↓
VectorizerRegistry
↓
VTracerVectorizer
```

---

# 99. Benchmark Dataset

Tạo:

```text
benchmark/pages/
```

Minimum:

```text
50 pages
```

Phân loại:

```text
10 sparse
10 dense
10 text-heavy
10 degraded paper
10 mixed difficult
```

Trang mẫu ban đầu phải nằm trong benchmark.

---

# 100. Ground Truth

Manual annotation:

```text
benchmark/annotations/
```

Mỗi illustration ground-truth geometry.

Metrics:

```text
recall
precision
IoU
candidate count
manual corrections required
```

---

# 101. Detection Target

V1 production target:

```text
Illustration recall ≥ 90%
```

Precision:

```text
≥ 75%
```

Nhưng metric quan trọng hơn:

```text
average manual operations/page
```

Goal:

```text
≤ 5 correction operations/page
```

trên benchmark target collection.

---

# 102. Performance Targets

25 MP source:

```text
thumbnail < 1 s typical
```

DeepZoom initial generation:

```text
< 5 s typical
```

OpenCV detection:

```text
< 3 s/page typical
```

Annotation interaction:

```text
target 60 FPS
```

---

# 103. Huge Image Test

Mandatory:

```text
12000 × 8000
```

Additional:

```text
20000 × 15000
```

Viewer phải:

```text
pan
zoom
annotate
```

mà không load full raster vào frontend memory.

---

# 104. Coordinate Regression Test

Given:

```text
MASTER
12000 × 8000
```

Create region via viewport.

Save.

Export.

Assert exact master crop.

Tolerance:

```text
±1 pixel
```

---

# 105. DeepZoom Regression

Verify:

```text
DZI generated
tiles readable
viewer dimensions == master dimensions
coordinate transforms stable
```

---

# 106. Polygon Tests

Must cover:

```text
convex
concave
many vertices
near-edge
self-intersection
multipolygon
```

---

# 107. Export Tests

Raster:

```text
dimensions
DPI
ICC
alpha
bit depth
lossless output
```

Vector:

```text
valid SVG
path count > 0
correct viewBox
no raster embedding
```

---

# 108. Project Recovery Test

Workflow:

```text
Import
Detect
Edit
Approve
Close
Restart
Open Project
```

Assert:

```text
geometry unchanged
statuses unchanged
sequence IDs unchanged
```

---

# 109. Batch Fault Tolerance

Simulated:

```text
Page 37 corrupted
```

Expected:

```text
36 processed
37 failed
38+ continue
```

Batch report shows failure.

---

# 110. Security

Local server bind default:

```text
127.0.0.1
```

Không:

```text
0.0.0.0
```

trừ developer override.

---

# 111. Data Privacy

Default:

```text
no telemetry
no uploads
no remote inference
```

Future cloud feature phải opt-in.

---

# 112. Phase 0 — Engineering Spike

Trước khi build product, thực hiện 4 spike nhỏ.

## Spike A

```text
OpenSeadragon
+
Annotorious
```

Goal:

- load DeepZoom;
- create rectangle;
- create polygon;
- edit polygon;
- recover master pixel coordinates.

## Spike B

```text
libvips
```

Goal:

- load 100 MP TIFF;
- generate DZI;
- crop arbitrary native-resolution rectangle;
- preserve metadata.

## Spike C

```text
VTracer
```

Goal:

- vectorize 20 representative illustrations;
- compare BW/adaptive settings;
- inspect node count/fidelity.

## Spike D

```text
OpenCV
```

Goal:

- detect candidate illustrations on 20 representative pages.

---

# 113. Phase 0 Exit Criteria

Không proceed nếu:

```text
OpenSeadragon ↔ master coordinates
```

không đạt pixel accuracy.

Không proceed nếu VTracer làm mất quá nhiều chi tiết line-art mà không tìm được viable preset.

---

# 114. Phase 1 — Project & Image Core

Implement:

- project schema;
- import;
- source/master;
- libvips;
- thumbnails;
- DeepZoom;
- project reopen;
- cache.

### Definition of Done

Import 100+ scans và xem tất cả bằng OpenSeadragon.

---

# 115. Phase 2 — Annotation Core

Implement:

- Annotorious integration;
- rectangle;
- polygon;
- rotated rectangle;
- canonical geometry adapter;
- annotation persistence;
- autosave;
- undo/redo.

### Definition of Done

Có thể crop hoàn toàn thủ công từ high-resolution master.

---

# 116. Phase 3 — Custom Region Tools

Implement:

- lasso;
- padding;
- fit-to-content;
- merge;
- split fallback;
- approve/reject;
- review mode.

### Definition of Done

Manual production workflow hoàn chỉnh dù chưa có detector.

---

# 117. Phase 4 — OpenCV Detector

Implement:

- normalization;
- thresholding;
- components;
- clustering;
- multi-scale grouping;
- filtering;
- profiles;
- debug overlay.

### Definition of Done

Benchmark đạt target recall.

---

# 118. Phase 5 — Batch Engine

Implement:

- worker pool;
- detection jobs;
- DeepZoom jobs;
- cancellation;
- progress;
- failure isolation.

### Definition of Done

500-page project không block UI.

---

# 119. Phase 6 — Raster Export

Implement:

```text
TIFF archive
PNG archive
transparent PNG
clean line-art PNG
batch export
manifest
```

### Definition of Done

Native crop source fidelity verified.

---

# 120. Phase 7 — VTracer Vector Export

Implement:

- preprocess;
- VTracer wrapper;
- presets;
- SVG validation;
- A/B preview;
- batch vectorization.

### Definition of Done

Representative line-art exports thành real SVG paths.

---

# 121. Phase 8 — Desktop Packaging

Implement:

```text
Electron
bundled backend
bundled libvips
bundled VTracer
installer
local backend lifecycle
```

Target:

```text
Windows x64
```

---

# 122. Phase 9 — Historical Document Experiments

After V1 stable:

Test:

```text
Eynollah
DocLayout-YOLO
```

Compare with OpenCV.

Metrics:

```text
recall
manual edits
processing time
hardware requirements
failure types
```

Không adopt AI provider nếu improvement không đáng kể.

---

# 123. Phase 10 — Interactive AI Segmentation

Optional:

```text
SAM2
```

Workflow:

```text
click / box
↓
mask
↓
polygon
↓
manual refine
```

Không ảnh hưởng baseline.

---

# 124. V1 Required Scope

Must ship:

- project create/open;
- folder import;
- high-res DeepZoom viewer;
- thumbnails;
- automatic OpenCV detection;
- rectangles;
- rotated rectangles;
- polygons;
- lasso;
- fit-to-content;
- merge;
- padding;
- approve/reject;
- undo/redo;
- autosave;
- review mode;
- TIFF export;
- PNG export;
- transparent PNG;
- SVG via VTracer;
- batch detection;
- batch export;
- failure reporting;
- offline operation.

---

# 125. Deferred Features

Post-V1:

```text
OCR
Han/Nom recognition
SAM2
DocLayout-YOLO
Eynollah production provider
Cloud
Accounts
Collaboration
Automatic semantic naming
Generative restoration
Full dewarping
PDF editing
```

---

# 126. Acceptance Criteria

## Viewer

- 100 MP image mở và zoom ổn định;
- frontend không load full image;
- tile navigation không làm mất annotation alignment.

## Annotation

- rectangle;
- rotated rectangle;
- arbitrary polygon;
- lasso;
- concave polygon;
- multipolygon internal support.

## Persistence

- annotation survives restart;
- no source overwrite;
- atomic saves.

## Detection

- batch;
- editable suggestions;
- ≥90% recall target benchmark.

## Export

- full master resolution;
- TIFF;
- PNG;
- alpha;
- SVG real paths.

## Performance

- no blocking UI;
- job cancellation;
- batch survives individual failures.

## Privacy

- works offline;
- localhost only;
- no telemetry default.

---

# 127. Release Blockers

Không release V1 nếu xảy ra bất kỳ điều nào:

```text
preview is used as export source

coordinate drift between viewer and master

source image can be overwritten

annotation corruption after restart

large TIFF causes frontend OOM

SVG output is raster embedded

one failed page crashes batch

autosave can truncate annotation JSON
```

---

# 128. Recommended Dev Reading Order

Dev nên đọc các repo theo thứ tự:

```text
1. Annotorious
2. OpenSeadragon
3. libvips / pyvips
4. ScanTailor Advanced
5. VTracer
6. Labelme
7. CVAT
8. LayoutParser
9. Eynollah
10. DocLayout-YOLO
11. SAM2
```

---

# 129. What To Reuse vs What To Build

## Reuse

```text
OpenSeadragon
→ image viewer

Annotorious
→ base annotation engine

libvips
→ image I/O + tiles + export

VTracer
→ SVG tracing

OpenCV
→ CV primitives
```

## Build

```text
project model
canonical annotation schema
coordinate adapter
historical illustration detector
review workflow
fit-to-content
merge/split workflow
padding system
export presets
batch job system
desktop packaging
```

---

# 130. Final Technical Baseline

```text
                           SOURCE
                              │
                              ▼
                           MASTER
                              │
                ┌─────────────┼──────────────┐
                │             │              │
                ▼             ▼              ▼
             libvips       OpenCV        preprocessing
                │             │
                │             ▼
                │         candidates
                │             │
                ▼             │
          DeepZoom tiles      │
                │             │
                ▼             │
          OpenSeadragon       │
                │             │
                └──────┬──────┘
                       ▼
                  Annotorious
                       │
                 USER REVIEW
                       │
                       ▼
                  ANNOTATIONS
                       │
            ┌──────────┼──────────┐
            │          │          │
            ▼          ▼          ▼
         ARCHIVE      CLEAN      VECTOR
       TIFF / PNG      PNG       VTracer
                                  │
                                  ▼
                                  SVG
```

---

# 131. Baseline Decisions — Locked

Các quyết định sau được xem là locked cho đến khi benchmark chứng minh cần thay đổi:

```text
React + TypeScript
OpenSeadragon
Annotorious
FastAPI
OpenCV
libvips / pyvips
VTracer
Electron

Local-first
Non-destructive
Master-pixel coordinates
Semi-automatic review
OpenCV default detector
SVG vector output
```

---

# 132. Product Principle

Illustration Extractor không được biến thành một generic annotation platform.

Nó phải tối ưu cho đúng workflow:

> **Import sách scan → tự tìm tranh → sửa vùng nhanh → export artwork chất lượng cao.**

Mọi feature mới phải được đánh giá theo câu hỏi:

> Feature này có giúp giảm thời gian tách illustration hoặc tăng chất lượng output hay không?

Nếu không, không đưa vào core product.