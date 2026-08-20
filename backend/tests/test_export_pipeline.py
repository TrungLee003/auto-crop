import csv
import json
import time
from pathlib import Path
import pytest
import pyvips
import cv2
import numpy as np

from app.annotation.models import (
    PolygonGeometry,
    RectangleGeometry,
    RegionExportSettings,
    RegionModel,
    RegionStatus,
)
from app.export.archive import export_archive_crop
from app.export.clean import export_clean_crop
from app.export.manifest import generate_catalog_csv, write_region_metadata_json
from app.export.models import ExportFormatOptions, ExportRequest, ExportScope
from app.export.vector import export_vector_svg


def test_export_individual_streams(tmp_path):
    # Create master image (1000x1000) with a circle drawing
    img = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    cv2.circle(img, (500, 500), 200, (30, 30, 30), -1)
    master_path = tmp_path / "master.png"
    cv2.imwrite(str(master_path), img)

    region = RegionModel(
        id="r_test",
        sequence=1,
        geometry=RectangleGeometry(x=250, y=250, width=500, height=500),
        status=RegionStatus.APPROVED,
        export=RegionExportSettings(archive=True, clean=True, vector=True)
    )

    # 1. Archive Stream
    archive_out = tmp_path / "archive.png"
    w, h = export_archive_crop(master_path, region, archive_out, dpi=300)
    assert archive_out.exists()
    assert w > 0 and h > 0

    # 2. Clean Stream (RGBA PNG)
    clean_out = tmp_path / "clean.png"
    w, h = export_clean_crop(master_path, region, clean_out, dpi=300)
    assert clean_out.exists()
    # Check alpha channel exists
    clean_img = cv2.imread(str(clean_out), cv2.IMREAD_UNCHANGED)
    assert clean_img.shape[2] == 4  # RGBA

    # 3. Vector Stream (SVG)
    vector_out = tmp_path / "vector.svg"
    ok = export_vector_svg(clean_out, vector_out)
    assert ok is True
    assert vector_out.exists()
    svg_content = vector_out.read_text(encoding="utf-8")
    assert "<svg" in svg_content
    assert "<path" in svg_content


def test_project_batch_export_pipeline(client, tmp_path):
    # Setup test project
    proj_dir = tmp_path / "Export_Project"
    resp = client.post("/api/v2/projects", json={"name": "Export Test", "path": str(proj_dir)})
    assert resp.status_code == 201
    proj_id = resp.json()["project_id"]

    # Create master image
    scan_path = tmp_path / "scan_p1.png"
    img = np.full((1200, 1200, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (200, 200), (500, 500), (20, 20, 20), -1)
    cv2.circle(img, (800, 800), 150, (30, 30, 30), -1)
    cv2.imwrite(str(scan_path), img)

    # Import
    imp_resp = client.post(f"/api/v2/projects/{proj_id}/imports", json={"file_paths": [str(scan_path)]})
    assert imp_resp.status_code == 200
    page_id = imp_resp.json()["pages"][0]["id"]

    # Add 2 approved regions (1 Rectangle, 1 Polygon)
    r1 = {
        "id": "r1",
        "sequence": 1,
        "geometry": {"type": "rectangle", "x": 150, "y": 150, "width": 400, "height": 400},
        "source": "manual",
        "status": "APPROVED",
        "export": {"archive": True, "clean": True, "vector": True}
    }
    r2 = {
        "id": "r2",
        "sequence": 2,
        "geometry": {
            "type": "polygon",
            "points": [[600, 600], [1000, 600], [1000, 1000], [600, 1000]]
        },
        "source": "manual",
        "status": "APPROVED",
        "export": {"archive": True, "clean": True, "vector": True}
    }
    client.post(f"/api/v2/pages/{page_id}/regions", json=r1)
    client.post(f"/api/v2/pages/{page_id}/regions", json=r2)

    # Trigger export via API
    exp_resp = client.post(f"/api/v2/projects/{proj_id}/export", json={
        "scope": "APPROVED_ONLY",
        "formats": {"archive": True, "clean": True, "vector": True},
        "archive_format": "PNG"
    })
    assert exp_resp.status_code == 200
    task_id = exp_resp.json()["task_id"]
    export_dir = Path(exp_resp.json()["export_dir"])

    # Poll task completion
    for _ in range(50):
        t_resp = client.get(f"/api/v2/tasks/{task_id}")
        assert t_resp.status_code == 200
        t_data = t_resp.json()
        if t_data["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert t_data["status"] == "completed"

    # Verify export artifacts on disk
    assert (export_dir / "catalog.csv").exists()
    assert (export_dir / "summary.json").exists()
    assert len(list((export_dir / "archive").glob("*.png"))) == 2
    assert len(list((export_dir / "clean").glob("*.png"))) == 2
    assert len(list((export_dir / "vector").glob("*.svg"))) == 2
    assert len(list((export_dir / "metadata").glob("*.json"))) == 2

    # Check catalog.csv content
    with open(export_dir / "catalog.csv", "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2

    # Check list exports API
    list_resp = client.get(f"/api/v2/projects/{proj_id}/exports")
    assert list_resp.status_code == 200
    exports_list = list_resp.json()
    assert len(exports_list) == 1
    assert exports_list[0]["total_regions"] == 2
