import os
from pathlib import Path
import pytest
import pyvips
import cv2
import numpy as np


@pytest.fixture
def sample_scans_dir(tmp_path):
    """Generate temporary scan images for testing."""
    scans_dir = tmp_path / "scans"
    scans_dir.mkdir()

    # Create scan 1: 1600x1200 RGB image with 300 DPI (8-bit uchar)
    img1 = (pyvips.Image.black(1600, 1200) + 240).cast("uchar")
    img1 = img1.bandjoin([img1, img1])
    # add some content
    r1 = (pyvips.Image.black(400, 300) + [200, 40, 40]).cast("uchar")
    img1 = img1.insert(r1, 200, 200)
    img1 = img1.copy(xres=300.0 / 25.4, yres=300.0 / 25.4)
    scan1_path = scans_dir / "scan_001.tif"
    img1.tiffsave(str(scan1_path))

    # Create scan 2: 1200x800 PNG image
    img2 = np.full((800, 1200, 3), 250, dtype=np.uint8)
    cv2.circle(img2, (600, 400), 200, (30, 150, 30), -1)
    scan2_path = scans_dir / "scan_002.png"
    cv2.imwrite(str(scan2_path), img2)

    return scans_dir


def test_phase1_full_pipeline(client, tmp_path, sample_scans_dir):
    # 1. Create project
    proj_dir = tmp_path / "Test_Book_Project"
    resp = client.post("/api/v2/projects", json={
        "name": "Historical Atlas",
        "path": str(proj_dir)
    })
    assert resp.status_code == 201
    proj_data = resp.json()
    project_id = proj_data["project_id"]
    assert proj_data["name"] == "Historical Atlas"
    assert (proj_dir / "project.json").exists()
    assert (proj_dir / "sources").is_dir()
    assert (proj_dir / "masters").is_dir()
    assert (proj_dir / "cache" / "thumbnails").is_dir()
    assert (proj_dir / "cache" / "deepzoom").is_dir()

    # 2. Import scans
    scan_files = [str(p) for p in sample_scans_dir.glob("*.*")]
    import_resp = client.post(f"/api/v2/projects/{project_id}/imports", json={
        "file_paths": scan_files,
        "mode": "COPY"
    })
    assert import_resp.status_code == 200
    import_data = import_resp.json()
    assert import_data["imported_count"] == 2
    assert import_data["skipped_duplicates"] == 0
    assert len(import_data["pages"]) == 2

    # 3. Check deduplication on second import
    import_dup = client.post(f"/api/v2/projects/{project_id}/imports", json={
        "file_paths": scan_files,
        "mode": "COPY"
    })
    assert import_dup.status_code == 200
    dup_data = import_dup.json()
    assert dup_data["imported_count"] == 0
    assert dup_data["skipped_duplicates"] == 2

    # 4. List pages
    pages_resp = client.get(f"/api/v2/projects/{project_id}/pages")
    assert pages_resp.status_code == 200
    pages = pages_resp.json()
    assert len(pages) == 2

    page1 = pages[0]
    page1_id = page1["id"]
    assert page1["width"] > 0
    assert page1["height"] > 0
    assert page1["status"] == "NEW"
    assert page1["thumbnail_path"] is not None
    assert page1["dzi_path"] is not None

    # 5. Fetch thumbnail
    thumb_resp = client.get(f"/api/v2/pages/{page1_id}/thumbnail")
    assert thumb_resp.status_code == 200
    assert thumb_resp.headers["content-type"] in ("image/jpeg", "image/jpg")
    assert len(thumb_resp.content) > 100

    # 6. Fetch viewer metadata
    viewer_resp = client.get(f"/api/v2/pages/{page1_id}/viewer")
    assert viewer_resp.status_code == 200
    viewer_info = viewer_resp.json()
    assert viewer_info["master_width"] == page1["width"]
    assert viewer_info["master_height"] == page1["height"]
    assert "dzi" in viewer_info["dzi_url"]

    # 7. Fetch DZI tile descriptor
    dzi_url = viewer_info["dzi_url"]
    dzi_resp = client.get(dzi_url)
    assert dzi_resp.status_code == 200
    assert "<Image" in dzi_resp.text
    assert "TileSize" in dzi_resp.text

    # 8. Fetch DeepZoom pyramid tile image directly (OpenSeadragon style request)
    tile_resp = client.get(f"/api/v2/tiles/{project_id}/{page1_id}/{page1_id}_files/0/0_0.jpeg")
    assert tile_resp.status_code == 200
    assert "image" in tile_resp.headers["content-type"]
    assert len(tile_resp.content) > 50

    # 9. Re-open project from disk
    open_resp = client.post("/api/v2/projects/open", json={"path": str(proj_dir)})
    assert open_resp.status_code == 200
    opened_proj = open_resp.json()
    assert opened_proj["project_id"] == project_id
    assert len(opened_proj["pages"]) == 2

    # 10. Delete page 2 from project
    page2_id = opened_proj["pages"][1]["id"]
    del_resp = client.delete(f"/api/v2/pages/{page2_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted_page_id"] == page2_id

    # Verify project now has 1 page
    p_resp = client.get(f"/api/v2/projects/{project_id}")
    assert p_resp.status_code == 200
    assert len(p_resp.json()["pages"]) == 1
