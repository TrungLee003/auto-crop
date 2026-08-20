import csv
import json
import time
from pathlib import Path
import pytest
import pyvips
import cv2
import numpy as np


def test_full_end_to_end_system_workflow(client, tmp_path):
    """
    Comprehensive End-to-End System Test (Phase 0 -> Phase 6):
    Project Creation -> Scan Import -> DZI Streaming -> Batch Auto-Detection ->
    Manual Drawing & Fit-to-Content -> Approval -> Multi-Stream Export -> Catalog.
    """
    # 1. Project Creation
    proj_dir = tmp_path / "E2E_Historical_Book"
    create_resp = client.post("/api/v2/projects", json={
        "name": "E2E Historical Book",
        "path": str(proj_dir)
    })
    assert create_resp.status_code == 201
    proj_data = create_resp.json()
    proj_id = proj_data["project_id"]
    assert (proj_dir / "project.json").exists()

    # 2. Create synthetic scan pages
    # Page 1: 2000x2000 with 2 distinct woodcuts
    p1_raw = np.full((2000, 2000, 3), 255, dtype=np.uint8)
    cv2.rectangle(p1_raw, (200, 200), (800, 800), (30, 30, 30), 4)
    cv2.circle(p1_raw, (500, 500), 150, (40, 40, 40), -1)
    cv2.rectangle(p1_raw, (1200, 1200), (1800, 1800), (30, 30, 30), 4)
    scan1_path = tmp_path / "page_001.png"
    cv2.imwrite(str(scan1_path), p1_raw)

    # Page 2: 2000x2000 with organic contour illustration
    p2_raw = np.full((2000, 2000, 3), 250, dtype=np.uint8)
    cv2.ellipse(p2_raw, (1000, 1000), (600, 400), 15, 0, 360, (20, 20, 20), 4)
    cv2.circle(p2_raw, (1000, 1000), 100, (40, 40, 40), -1)
    scan2_path = tmp_path / "page_002.png"
    cv2.imwrite(str(scan2_path), p2_raw)

    # 3. Import Scans
    imp_resp = client.post(f"/api/v2/projects/{proj_id}/imports", json={
        "file_paths": [str(scan1_path), str(scan2_path)],
        "mode": "COPY"
    })
    assert imp_resp.status_code == 200
    pages = imp_resp.json()["pages"]
    assert len(pages) == 2
    page1_id = pages[0]["id"]
    page2_id = pages[1]["id"]

    # 4. DeepZoom Tile Viewer Metadata Verification
    viewer_resp = client.get(f"/api/v2/pages/{page1_id}/viewer")
    assert viewer_resp.status_code == 200
    v_data = viewer_resp.json()
    assert v_data["master_width"] == 2000
    assert v_data["master_height"] == 2000
    assert "dzi" in v_data["dzi_url"]

    # 5. Batch Auto-Detection Pipeline
    batch_resp = client.post(f"/api/v2/projects/{proj_id}/batch-detect", json={
        "filter_status": "ALL"
    })
    assert batch_resp.status_code == 200
    task_id = batch_resp.json()["task_id"]

    # Poll detection task
    for _ in range(50):
        t_resp = client.get(f"/api/v2/tasks/{task_id}")
        t_data = t_resp.json()
        if t_data["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert t_data["status"] == "completed"

    # Verify Page 1 detected regions
    p1_regions_resp = client.get(f"/api/v2/pages/{page1_id}/regions")
    assert p1_regions_resp.status_code == 200
    p1_regions = p1_regions_resp.json()
    assert len(p1_regions) >= 2

    # 6. Manual Custom Region (Rotated Rectangle & Fit-to-Content)
    rot_region = {
        "id": "manual_rot",
        "sequence": len(p1_regions) + 1,
        "geometry": {
            "type": "rotated_rectangle",
            "cx": 500,
            "cy": 500,
            "width": 620,
            "height": 620,
            "angle": 12.5
        },
        "source": "manual",
        "status": "APPROVED",
        "export": {"archive": True, "clean": True, "vector": True}
    }
    add_resp = client.post(f"/api/v2/pages/{page1_id}/regions", json=rot_region)
    assert add_resp.status_code == 201

    # Fit-to-content on manual region
    fit_resp = client.post(f"/api/v2/pages/{page1_id}/regions/manual_rot/fit")
    assert fit_resp.status_code == 200

    # Approve all regions on page 1
    app_resp = client.post(f"/api/v2/pages/{page1_id}/approve-all")
    assert app_resp.status_code == 200

    # 7. Multi-Stream Export Pipeline
    exp_resp = client.post(f"/api/v2/projects/{proj_id}/export", json={
        "scope": "APPROVED_ONLY",
        "formats": {"archive": True, "clean": True, "vector": True},
        "archive_format": "PNG"
    })
    assert exp_resp.status_code == 200
    exp_task_id = exp_resp.json()["task_id"]
    export_dir = Path(exp_resp.json()["export_dir"])

    # Poll export task
    for _ in range(50):
        t_resp = client.get(f"/api/v2/tasks/{exp_task_id}")
        t_data = t_resp.json()
        if t_data["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert t_data["status"] == "completed"

    # 8. Verify all Export Outputs
    assert (export_dir / "catalog.csv").exists()
    assert (export_dir / "summary.json").exists()

    archive_files = list((export_dir / "archive").glob("*.png"))
    clean_files = list((export_dir / "clean").glob("*.png"))
    vector_files = list((export_dir / "vector").glob("*.svg"))
    meta_files = list((export_dir / "metadata").glob("*.json"))

    assert len(archive_files) >= 2
    assert len(clean_files) >= 2
    assert len(vector_files) >= 2
    assert len(meta_files) >= 2

    # Verify SVG vector has valid SVG paths
    for vf in vector_files:
        content = vf.read_text(encoding="utf-8")
        assert "<svg" in content
        assert "<path" in content

    # Verify Catalog CSV
    with open(export_dir / "catalog.csv", "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        assert len(rows) >= 2
        assert "archive_file" in rows[0]
        assert "clean_file" in rows[0]
        assert "vector_file" in rows[0]
