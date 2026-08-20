import json
from pathlib import Path
import pytest
import pyvips
import cv2
import numpy as np

from app.geometry.transforms import simplify_polygon_rdp, merge_geometries, nudge_geometry
from app.geometry.snapping import fit_region_to_ink_content
from app.annotation.models import (
    RectangleGeometry,
    PolygonGeometry,
    RotatedRectangleGeometry,
    RegionModel,
)


def test_rdp_simplification_and_merge():
    # 1. RDP simplification: a straight line with 10 intermediate jittery points
    dense_pts = [[float(i), float(i % 2) * 0.5] for i in range(20)]
    dense_pts.extend([[20.0, 10.0], [0.0, 10.0]])
    simplified = simplify_polygon_rdp(dense_pts, tolerance=1.0)
    assert len(simplified) < len(dense_pts)
    assert len(simplified) >= 3

    # 2. Merge 2 overlapping rectangles
    r1 = RectangleGeometry(x=100, y=100, width=200, height=200)
    r2 = RectangleGeometry(x=200, y=100, width=200, height=200)
    merged = merge_geometries([r1, r2])
    assert merged.type == "polygon"
    assert len(merged.points) >= 4

    # 3. Nudge
    nudged = nudge_geometry(r1, dx=10.0, dy=-5.0)
    assert nudged.x == 110.0
    assert nudged.y == 95.0


def test_fit_to_content_and_api(client, tmp_path):
    # Setup test project
    proj_dir = tmp_path / "Fit_Project"
    resp = client.post("/api/v2/projects", json={"name": "Fit Test", "path": str(proj_dir)})
    assert resp.status_code == 201
    proj_id = resp.json()["project_id"]

    # Create synthetic test page: white background with an ink drawing strictly between (300, 300) and (500, 500)
    img = np.full((1200, 1200, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (320, 320), (480, 480), (30, 30, 30), 4)
    cv2.circle(img, (400, 400), 50, (40, 40, 40), -1)

    scan_path = tmp_path / "scan_fit.png"
    cv2.imwrite(str(scan_path), img)

    imp_resp = client.post(f"/api/v2/projects/{proj_id}/imports", json={"file_paths": [str(scan_path)]})
    assert imp_resp.status_code == 200
    page_id = imp_resp.json()["pages"][0]["id"]

    # 1. Add a very loose / oversized bounding box: (100, 100) to (800, 800)
    loose_rect = {
        "id": "r_loose",
        "sequence": 1,
        "geometry": {"type": "rectangle", "x": 150, "y": 150, "width": 650, "height": 650},
        "source": "manual",
        "status": "EDITED"
    }
    client.post(f"/api/v2/pages/{page_id}/regions", json=loose_rect)

    # 2. Add second region for merge test
    r2 = {
        "id": "r2",
        "sequence": 2,
        "geometry": {"type": "rectangle", "x": 700, "y": 700, "width": 100, "height": 100},
        "source": "manual",
        "status": "EDITED"
    }
    client.post(f"/api/v2/pages/{page_id}/regions", json=r2)

    # 3. Call Fit-to-content API on r_loose
    fit_resp = client.post(f"/api/v2/pages/{page_id}/regions/r_loose/fit")
    assert fit_resp.status_code == 200
    fitted = fit_resp.json()
    geom = fitted["geometry"]
    assert geom["type"] == "rectangle"
    # Fitted bounds should now tightly hug (320, 320, 160, 160) +/- padding
    assert abs(geom["x"] - 300) <= 25
    assert abs(geom["y"] - 300) <= 25
    assert abs(geom["width"] - 200) <= 40
    assert abs(geom["height"] - 200) <= 40

    # 4. Call Merge API on 2 regions
    merge_resp = client.post(f"/api/v2/pages/{page_id}/regions/merge", json={
        "region_ids": ["r_loose", "r2"]
    })
    assert merge_resp.status_code == 200
    merged_region = merge_resp.json()
    assert merged_region["geometry"]["type"] in ("polygon", "multipolygon")

    # Verify only 1 region remains on page
    final_regions = client.get(f"/api/v2/pages/{page_id}/regions").json()
    assert len(final_regions) == 1
