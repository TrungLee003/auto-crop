import asyncio
import time
from pathlib import Path
import pytest
import pyvips
import cv2
import numpy as np

from app.detection.opencv import OpenCVDetector
from app.detection.base import DetectionConfig
from app.detection.service import detection_service


def test_opencv_detector_direct(tmp_path):
    # Create 2000x2000 image with 2 separate illustrations on white background
    img = np.full((2000, 2000, 3), 255, dtype=np.uint8)
    # Illustration 1: Top-Left (200, 200) to (700, 700)
    cv2.rectangle(img, (200, 200), (700, 700), (30, 30, 30), 4)
    cv2.circle(img, (450, 450), 100, (40, 40, 40), -1)

    # Illustration 2: Bottom-Right (1200, 1200) to (1700, 1700)
    cv2.rectangle(img, (1200, 1200), (1700, 1700), (30, 30, 30), 4)
    for r in range(40, 200, 30):
        cv2.circle(img, (1450, 1450), r, (50, 50, 50), 2)

    master_path = tmp_path / "master_test.png"
    cv2.imwrite(str(master_path), img)

    detector = OpenCVDetector()
    regions = detector.detect(master_path, DetectionConfig())

    assert len(regions) == 2
    assert all(r.source == "auto" for r in regions)
    assert all(r.status == "AUTO" for r in regions)

    # Verify bounding boxes are reasonably close to ground truth
    r1 = next(r for r in regions if r.geometry.x < 1000)
    assert abs(r1.geometry.x - 200) < 50
    assert abs(r1.geometry.y - 200) < 50


def test_detection_api_and_batch_pipeline(client, tmp_path):
    # Setup test project
    proj_dir = tmp_path / "Detect_Project"
    resp = client.post("/api/v2/projects", json={"name": "Detection Test", "path": str(proj_dir)})
    assert resp.status_code == 201
    proj_id = resp.json()["project_id"]

    # Create 2 test scan pages
    scan1_path = tmp_path / "page_01.png"
    img1 = np.full((1500, 1500, 3), 255, dtype=np.uint8)
    cv2.rectangle(img1, (300, 300), (800, 800), (20, 20, 20), -1)
    cv2.imwrite(str(scan1_path), img1)

    scan2_path = tmp_path / "page_02.png"
    img2 = np.full((1500, 1500, 3), 255, dtype=np.uint8)
    cv2.rectangle(img2, (200, 200), (600, 600), (20, 20, 20), -1)
    cv2.rectangle(img2, (900, 900), (1300, 1300), (20, 20, 20), -1)
    cv2.imwrite(str(scan2_path), img2)

    # Import pages
    imp_resp = client.post(f"/api/v2/projects/{proj_id}/imports", json={
        "file_paths": [str(scan1_path), str(scan2_path)]
    })
    assert imp_resp.status_code == 200
    pages = imp_resp.json()["pages"]
    assert len(pages) == 2
    page1_id = pages[0]["id"]
    page2_id = pages[1]["id"]

    # 1. Test single page auto-detect API
    det_resp = client.post(f"/api/v2/pages/{page1_id}/detect")
    assert det_resp.status_code == 200
    p1_regions = det_resp.json()
    assert len(p1_regions) >= 1
    assert p1_regions[0]["status"] == "AUTO"

    # 2. Test approve-all API
    app_resp = client.post(f"/api/v2/pages/{page1_id}/approve-all")
    assert app_resp.status_code == 200
    approved_regions = app_resp.json()
    assert all(r["status"] == "APPROVED" for r in approved_regions)

    # 3. Test Batch Detection API
    batch_resp = client.post(f"/api/v2/projects/{proj_id}/batch-detect", json={
        "filter_status": "ALL"
    })
    assert batch_resp.status_code == 200
    task_id = batch_resp.json()["task_id"]
    assert task_id

    # 4. Poll task status until complete
    for _ in range(50):
        task_resp = client.get(f"/api/v2/tasks/{task_id}")
        assert task_resp.status_code == 200
        task_data = task_resp.json()
        if task_data["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert task_data["status"] == "completed"
    assert task_data["progress"] == 100.0

    # 5. Verify page 2 has auto-detected regions
    p2_regions_resp = client.get(f"/api/v2/pages/{page2_id}/regions")
    assert p2_regions_resp.status_code == 200
    p2_regions = p2_regions_resp.json()
    assert len(p2_regions) >= 2
