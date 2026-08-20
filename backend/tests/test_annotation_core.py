import os
import json
from pathlib import Path
import pytest
import pyvips
from app.geometry.transforms import compute_bounding_box, apply_padding
from app.geometry.validation import validate_polygon, fix_polygon_points
from app.annotation.models import (
    Padding,
    PolygonGeometry,
    RectangleGeometry,
    RegionModel,
    RegionStatus,
    RotatedRectangleGeometry,
)


def test_geometry_validation_and_transforms():
    # 1. Valid triangle
    valid_pts = [[0.0, 0.0], [100.0, 0.0], [50.0, 100.0]]
    ok, err = validate_polygon(valid_pts)
    assert ok is True
    assert err is None

    # 2. Degenerate (< 3 pts)
    ok, err = validate_polygon([[0.0, 0.0], [10.0, 10.0]])
    assert ok is False

    # 3. Self-intersecting hourglass
    bow_tie = [[0.0, 0.0], [100.0, 100.0], [100.0, 0.0], [0.0, 100.0]]
    ok, err = validate_polygon(bow_tie)
    assert ok is False

    # 4. Repair polygon
    repaired = fix_polygon_points(bow_tie)
    assert len(repaired) >= 3

    # 5. Bounding box & padding
    rect = RectangleGeometry(x=100.0, y=200.0, width=500.0, height=400.0)
    bounds = compute_bounding_box(rect)
    assert bounds == (100.0, 200.0, 600.0, 600.0)

    pad = Padding(top=40, right=40, bottom=40, left=40)
    crop_x, crop_y, crop_w, crop_h = apply_padding(bounds, pad, max_w=2000, max_h=2000)
    assert crop_x == 60
    assert crop_y == 160
    assert crop_w == 580
    assert crop_h == 480


def test_annotation_persistence_and_api(client, tmp_path):
    # Setup test project
    proj_dir = tmp_path / "Anno_Project"
    resp = client.post("/api/v2/projects", json={"name": "Anno Test", "path": str(proj_dir)})
    assert resp.status_code == 201
    proj = resp.json()
    project_id = proj["project_id"]

    # Create dummy scan & import
    scan_file = tmp_path / "page_1.png"
    img = (pyvips.Image.black(1000, 1000) + 255).cast("uchar")
    img = img.bandjoin([img, img])
    img.pngsave(str(scan_file))

    imp_resp = client.post(f"/api/v2/projects/{project_id}/imports", json={"file_paths": [str(scan_file)]})
    assert imp_resp.status_code == 200
    page = imp_resp.json()["pages"][0]
    page_id = page["id"]

    # 1. Add Rectangle region
    rect_region = {
        "id": "r1",
        "sequence": 1,
        "geometry": {"type": "rectangle", "x": 100, "y": 150, "width": 400, "height": 300},
        "source": "manual",
        "status": "APPROVED",
        "padding": {"top": 20, "right": 20, "bottom": 20, "left": 20}
    }
    add_resp = client.post(f"/api/v2/pages/{page_id}/regions", json=rect_region)
    assert add_resp.status_code == 201
    added_r1 = add_resp.json()
    assert added_r1["id"] == "r1"
    assert added_r1["geometry"]["type"] == "rectangle"

    # 2. Add Polygon region
    poly_region = {
        "id": "r2",
        "sequence": 2,
        "geometry": {
            "type": "polygon",
            "points": [[600, 200], [800, 200], [850, 500], [550, 450]]
        },
        "source": "manual",
        "status": "EDITED"
    }
    add_resp2 = client.post(f"/api/v2/pages/{page_id}/regions", json=poly_region)
    assert add_resp2.status_code == 201

    # 3. Add Rotated Rectangle region
    rot_region = {
        "id": "r3",
        "sequence": 3,
        "geometry": {
            "type": "rotated_rectangle",
            "cx": 400,
            "cy": 700,
            "width": 300,
            "height": 200,
            "angle": 15.0
        },
        "source": "manual",
        "status": "AUTO"
    }
    add_resp3 = client.post(f"/api/v2/pages/{page_id}/regions", json=rot_region)
    assert add_resp3.status_code == 201

    # 4. Fetch all regions
    get_resp = client.get(f"/api/v2/pages/{page_id}/regions")
    assert get_resp.status_code == 200
    regions = get_resp.json()
    assert len(regions) == 3
    assert regions[0]["id"] == "r1"
    assert regions[1]["id"] == "r2"
    assert regions[2]["id"] == "r3"

    # 5. Check persistence file on disk
    anno_file = proj_dir / "annotations" / f"{page_id}.json"
    assert anno_file.exists()
    data = json.loads(anno_file.read_text(encoding="utf-8"))
    assert len(data["regions"]) == 3

    # 6. Bulk update (e.g. modify status & delete r2)
    regions[0]["status"] = "EDITED"
    updated_list = [regions[0], regions[2]]
    put_resp = client.put(f"/api/v2/pages/{page_id}/regions", json=updated_list)
    assert put_resp.status_code == 200
    new_regions = put_resp.json()
    assert len(new_regions) == 2
    assert new_regions[0]["status"] == "EDITED"
    assert (proj_dir / "annotations" / f"{page_id}.json.bak").exists()

    # 7. Delete single region
    del_resp = client.delete(f"/api/v2/pages/{page_id}/regions/{new_regions[1]['id']}")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["status"] == "ok"

    final_resp = client.get(f"/api/v2/pages/{page_id}/regions")
    assert len(final_resp.json()) == 1
