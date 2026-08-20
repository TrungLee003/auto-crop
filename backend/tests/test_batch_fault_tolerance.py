import csv
import json
import time
from pathlib import Path
import cv2
import numpy as np
import pytest

from app.project.models import PageStatus


def test_batch_detection_fault_tolerance(client, tmp_path):
    """
    Section 109 & Section 127 Blocker 7:
    Verify that if a page in a batch is corrupted or unreadable,
    the batch detection isolates the error, marks the failed page as FAILED,
    and successfully continues detecting the remaining valid pages.
    """
    proj_dir = tmp_path / "Fault_Tolerance_Project"
    resp = client.post("/api/v2/projects", json={"name": "Fault Tolerance Test", "path": str(proj_dir)})
    assert resp.status_code == 201
    proj_id = resp.json()["project_id"]

    # 1. Create Page 1: Valid scan with circle
    scan1 = tmp_path / "scan_01.png"
    img1 = np.full((800, 800, 3), 255, dtype=np.uint8)
    cv2.circle(img1, (400, 400), 150, (0, 0, 0), -1)
    cv2.imwrite(str(scan1), img1)

    # 2. Create Page 2: Valid scan with rectangle
    scan2 = tmp_path / "scan_02.png"
    img2 = np.full((800, 800, 3), 255, dtype=np.uint8)
    cv2.rectangle(img2, (200, 200), (600, 600), (20, 20, 20), -1)
    cv2.imwrite(str(scan2), img2)

    # 3. Create Page 3: Valid scan with drawing
    scan3 = tmp_path / "scan_03.png"
    img3 = np.full((800, 800, 3), 255, dtype=np.uint8)
    cv2.circle(img3, (300, 300), 100, (30, 30, 30), -1)
    cv2.imwrite(str(scan3), img3)

    # Import all 3 pages
    imp_resp = client.post(
        f"/api/v2/projects/{proj_id}/imports",
        json={"file_paths": [str(scan1), str(scan2), str(scan3)]}
    )
    assert imp_resp.status_code == 200
    pages = imp_resp.json()["pages"]
    assert len(pages) == 3

    page1_id = pages[0]["id"]
    page2_id = pages[1]["id"]
    page3_id = pages[2]["id"]

    # Intentionally corrupt the master image of Page 2 (corrupted binary data)
    page2_master = proj_dir / pages[1]["master_path"]
    with open(page2_master, "wb") as f:
        f.write(b"CORRUPTED_NON_IMAGE_DATA_1234567890")

    # Run batch detection across all NEW pages
    batch_resp = client.post(f"/api/v2/projects/{proj_id}/batch-detect", json={"filter_status": "NEW"})
    assert batch_resp.status_code == 200
    task_id = batch_resp.json()["task_id"]

    # Poll task completion
    for _ in range(50):
        t_resp = client.get(f"/api/v2/tasks/{task_id}")
        assert t_resp.status_code == 200
        t_data = t_resp.json()
        if t_data["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    # Assert batch task completed successfully without crashing
    assert t_data["status"] == "completed"
    assert "1 failed" in t_data["message"] or t_data["progress"] == 100.0

    # Verify Page 1 was successfully detected
    p1_resp = client.get(f"/api/v2/pages/{page1_id}")
    assert p1_resp.status_code == 200
    p1_data = p1_resp.json()
    assert p1_data["status"] in (PageStatus.IN_REVIEW.value, PageStatus.DETECTED.value)

    p1_regions = client.get(f"/api/v2/pages/{page1_id}/regions").json()
    assert len(p1_regions) >= 1

    # Verify Page 2 was isolated and marked as FAILED with warning
    p2_resp = client.get(f"/api/v2/pages/{page2_id}")
    assert p2_resp.status_code == 200
    p2_data = p2_resp.json()
    assert p2_data["status"] == PageStatus.FAILED.value
    assert len(p2_data["warnings"]) >= 1

    # Verify Page 3 was successfully detected after the failure on Page 2
    p3_resp = client.get(f"/api/v2/pages/{page3_id}")
    assert p3_resp.status_code == 200
    p3_data = p3_resp.json()
    assert p3_data["status"] in (PageStatus.IN_REVIEW.value, PageStatus.DETECTED.value)

    p3_regions = client.get(f"/api/v2/pages/{page3_id}/regions").json()
    assert len(p3_regions) >= 1


def test_batch_export_fault_tolerance_and_jobs_api(client, tmp_path):
    """
    Section 109: Verify batch export continues and generates valid outputs
    even if one region/master is corrupt or missing. Also tests the unified /jobs API.
    """
    proj_dir = tmp_path / "Export_FT_Project"
    resp = client.post("/api/v2/projects", json={"name": "Export FT Test", "path": str(proj_dir)})
    assert resp.status_code == 201
    proj_id = resp.json()["project_id"]

    # Create 2 scans
    scan1 = tmp_path / "s1.png"
    img1 = np.full((600, 600, 3), 255, dtype=np.uint8)
    cv2.circle(img1, (300, 300), 100, (10, 10, 10), -1)
    cv2.imwrite(str(scan1), img1)

    scan2 = tmp_path / "s2.png"
    img2 = np.full((600, 600, 3), 255, dtype=np.uint8)
    cv2.rectangle(img2, (100, 100), (400, 400), (10, 10, 10), -1)
    cv2.imwrite(str(scan2), img2)

    imp = client.post(f"/api/v2/projects/{proj_id}/imports", json={"file_paths": [str(scan1), str(scan2)]}).json()
    p1_id = imp["pages"][0]["id"]
    p2_id = imp["pages"][1]["id"]

    # Add approved region to each page
    r1 = {
        "id": "r1",
        "sequence": 1,
        "geometry": {"type": "rectangle", "x": 100, "y": 100, "width": 400, "height": 400},
        "source": "manual",
        "status": "APPROVED",
        "export": {"archive": True, "clean": True, "vector": True}
    }
    r2 = {
        "id": "r2",
        "sequence": 2,
        "geometry": {"type": "rectangle", "x": 100, "y": 100, "width": 300, "height": 300},
        "source": "manual",
        "status": "APPROVED",
        "export": {"archive": True, "clean": True, "vector": True}
    }
    client.post(f"/api/v2/pages/{p1_id}/regions", json=r1)
    client.post(f"/api/v2/pages/{p2_id}/regions", json=r2)

    # Intentionally delete the master file for page 2
    p2_master = proj_dir / imp["pages"][1]["master_path"]
    if p2_master.exists():
        p2_master.unlink()

    # Trigger export
    exp_resp = client.post(f"/api/v2/projects/{proj_id}/export", json={
        "scope": "APPROVED_ONLY",
        "formats": {"archive": True, "clean": True, "vector": True},
        "archive_format": "PNG"
    })
    assert exp_resp.status_code == 200
    task_id = exp_resp.json()["task_id"]
    export_dir = Path(exp_resp.json()["export_dir"])

    # Test /api/v2/jobs API
    job_resp = client.get(f"/api/v2/jobs/{task_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["id"] == task_id

    jobs_list = client.get("/api/v2/jobs").json()
    assert any(j["id"] == task_id for j in jobs_list)

    # Poll completion
    for _ in range(50):
        t_resp = client.get(f"/api/v2/tasks/{task_id}")
        if t_resp.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert t_resp.json()["status"] == "completed"

    # Verify Page 1 export files exist
    assert (export_dir / "catalog.csv").exists()
    assert (export_dir / "summary.json").exists()
    assert len(list((export_dir / "archive").glob("*.png"))) >= 1
    assert len(list((export_dir / "clean").glob("*.png"))) >= 1
    assert len(list((export_dir / "vector").glob("*.svg"))) >= 1
