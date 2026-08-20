# Illustration Extractor

**Tách và xuất hàng loạt hình minh họa riêng lẻ từ sách scan, atlas, tài liệu và ấn bản lịch sử độ phân giải cao.**

> *Automation proposes. Human approves.*

---

## 🌟 Tính năng nổi bật (Key Features)

- **Local-First & Non-Destructive**: 100% xử lý cục bộ trên máy tính người dùng, không tải dữ liệu lên đám mây, bảo toàn tuyệt đối ảnh gốc.
- **DeepZoom Multi-Scale Tile Viewer**: Xem và tương tác với các bản scan siêu phân giải (4K, 8K, 50MP+) mượt mà qua OpenSeadragon.
- **Auto-Detection Engine (OpenCV)**: Thuật toán nhận diện tự động tối ưu riêng cho các bản scan tài liệu lịch sử (khử viền gáy sách, trừ nền Gaussian, ngưỡng thích ứng Otsu).
- **Bộ công cụ vẽ & chỉnh sửa trực quan (Interactive Annotation)**:
  - `Select (V)`: Click chọn hộp, kéo cạnh để di chuyển (120 FPS), kéo 4 góc để co giãn, xoay góc tự do.
  - `Rectangle (R)`: Vẽ hộp chữ nhật kinh điển.
  - `Rotated Rectangle (O)`: Vẽ hộp chữ nhật xoay theo độ nghiêng hình minh họa.
  - `Polygon (P)`: Vẽ đa giác tùy biến theo đường viền phức tạp.
  - `Lasso (L)`: Vẽ tự do bằng chuột, tự động làm mịn đường cong bằng Ramer–Douglas–Peucker (RDP).
  - `Fit to Content (F)`: Tự động co khít viền hộp vào nét mực thực tế.
  - `Merge (M)`: Gộp nhiều vùng chọn liền kề.
  - `Undo / Redo (Ctrl+Z / Ctrl+Shift+Z)`: Hoàn tác đa cấp độ.
- **Sắp xếp tự nhiên (Natural Sort Order)**: Sắp xếp danh sách trang theo thứ tự số tự nhiên (`1, 2, ... 10, ... 100`).
- **Xuất đa định dạng (Multi-Stream Export Pipeline)**:
  - `Archive`: Ảnh gốc không nén (TIFF / Lossless PNG).
  - `Clean Cutout`: Tách nền trong suốt (Transparent PNG) cho thiết kế.
  - `Vectorized`: Vector hóa độ nét cao (Scalable Vector SVG qua VTracer).
- **Batch Processing**: Chạy nhận diện và xuất hàng loạt toàn bộ sách hàng trăm trang song song và có khả năng chịu lỗi (fault-tolerant).

---

## 🏗️ Kiến trúc hệ thống (Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                       FRONTEND LAYER                        │
│   React 18 + TypeScript + Vite + TailwindCSS + Radix UI     │
│       OpenSeadragon DeepZoom Canvas + SVG Overlay Layer     │
│                 Zustand State Management                    │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST API (FastAPI)
┌──────────────────────────────▼──────────────────────────────┐
│                       BACKEND LAYER                         │
│   FastAPI + Uvicorn + libvips (pyvips) + OpenCV + VTracer   │
│                                                             │
│   • Master & Pyramid Service (DZI + DeepZoom Tile Cache)    │
│   • Historical Detection Engine (Otsu + Background Sub)     │
│   • Vectorization Pipeline (VTracer Vectorizer)             │
│   • Batch Job Manager & Worker Queue                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Cài đặt & Khởi chạy (Getting Started)

### Yêu cầu hệ thống (Prerequisites)
- **Python**: 3.11 hoặc 3.12 (khuyến nghị dùng `uv` package manager)
- **Node.js**: 18+ (khuyến nghị dùng `pnpm`)
- **libvips**: Hỗ trợ xử lý ảnh lớn tốc độ cao

---

### Khởi chạy nhanh (Quick Start)

#### 1. Cài đặt Dependencies

```powershell
# Cài đặt toàn bộ dependencies tự động
.\scripts\setup.ps1
```

#### 2. Khởi chạy môi trường phát triển (Dev Servers)

```powershell
# Khởi chạy cả Backend và Frontend
.\scripts\dev.ps1
```

Hoặc khởi chạy thủ công từng phần:

```powershell
# Terminal 1 - Backend (FastAPI: http://127.0.0.1:8000)
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 - Frontend (Vite: http://127.0.0.1:5173)
cd frontend
pnpm install
pnpm dev
```

---

## ⌨️ Phím tắt thao tác (Keyboard Shortcuts)

| Phím tắt | Thao tác |
|---|---|
| `V` | Công cụ Chọn (`Select`) |
| `R` | Công cụ Vẽ hình chữ nhật (`Rectangle`) |
| `O` | Công cụ Vẽ hình chữ nhật xoay (`Rotated Rect`) |
| `P` | Công cụ Vẽ đa giác (`Polygon`) |
| `L` | Công cụ Vẽ tự do (`Lasso`) |
| `Space + Kéo chuột` | Di chuyển khung nhìn (Pan canvas) |
| `Cuộn chuột` | Phóng to / Thu nhỏ (Zoom in/out) |
| `F` | Khớp sát nội dung nét vẽ (`Fit to Content`) |
| `M` | Gộp các vùng chọn (`Merge`) |
| `Delete` / `Backspace` | Xóa vùng chọn |
| `Ctrl + Z` | Hoàn tác (`Undo`) |
| `Ctrl + Shift + Z` | Làm lại (`Redo`) |
| `A` | Duyệt / Chấp thuận trang (`Approve Page`) |
| `[` / `]` | Chuyển trang trước / trang kế tiếp |

---

## 📁 Cấu trúc thư mục (Project Structure)

```
illustration-extractor/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI Routers (Projects, Pages, Detection, Export)
│   │   ├── detection/      # OpenCV detection algorithms
│   │   ├── images/         # pyvips Master & DeepZoom pyramid generator
│   │   ├── vector/         # VTracer SVG vectorization engine
│   │   ├── project/        # Project & page serialization
│   │   └── tiles/          # DeepZoom tile server
│   ├── tests/              # Pytest test suite (26 passing tests)
│   └── pyproject.toml      # Python dependencies & config
├── frontend/
│   ├── src/
│   │   ├── annotation/     # SVG Annotation Layer & Geometry Adapters
│   │   ├── viewer/         # OpenSeadragon DeepZoom viewer
│   │   ├── pages/          # Sidebar & Page Navigator
│   │   ├── review/         # Region Inspector & Export Options
│   │   ├── stores/         # Zustand stores (projectStore, pageStore, annotationStore)
│   │   └── components/     # Toolbars, Dialogs & UI components
│   └── package.json        # Frontend dependencies & scripts
├── docs/                   # Tài liệu thiết kế & đặc tả kỹ thuật
└── scripts/                # Scripts khởi chạy & cài đặt (dev.ps1, setup.ps1)
```

---

## 🧪 Kiểm thử chất lượng (Verification & Tests)

```powershell
# Chạy toàn bộ Backend Tests (26 tests)
cd backend
uv run --python 3.12 pytest -v

# Kiểm tra kiểu dữ liệu & Build Frontend
cd frontend
pnpm typecheck
pnpm build
```

---

## 📄 Bản quyền (License)

Dự án được phát triển phục vụ mục đích xử lý tài liệu lịch sử, số hóa ấn bản mỹ thuật và sách scan cổ.
