from pathlib import Path
import pytest
import cv2
import numpy as np

from app.annotation.models import RectangleGeometry, RegionExportSettings, RegionModel, RegionStatus
from app.export.vector import BUILTIN_PRESETS, generate_vector_preview


def test_vector_presets_and_preview(tmp_path):
    # Create test image with line art
    img = np.full((800, 800, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (400, 400), (0, 0, 0), 4)
    cv2.circle(img, (250, 250), 80, (0, 0, 0), -1)
    master_path = tmp_path / "master.png"
    cv2.imwrite(str(master_path), img)

    region = RegionModel(
        id="r_vec_test",
        sequence=1,
        geometry=RectangleGeometry(x=50, y=50, width=450, height=450),
        status=RegionStatus.APPROVED,
        export=RegionExportSettings(archive=True, clean=True, vector=True)
    )

    # Test all 3 builtin presets
    for preset_id in ["historical_bw", "detailed_engraving", "color_lithograph"]:
        res = generate_vector_preview(
            master_path=master_path,
            region=region,
            preset_id=preset_id
        )
        assert "<svg" in res["svg_content"]
        assert "<path" in res["svg_content"]
        assert res["path_count"] >= 1
        assert res["file_size_bytes"] > 0
        assert res["elapsed_ms"] > 0


def test_vector_preview_api(client, tmp_path):
    # Setup test project & page
    proj_dir = tmp_path / "Vec_Proj"
    resp = client.post("/api/v2/projects", json={"name": "Vec Test", "path": str(proj_dir)})
    assert resp.status_code == 201
    proj_id = resp.json()["project_id"]

    scan_path = tmp_path / "scan_p1.png"
    img = np.full((800, 800, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (150, 150), (450, 450), (10, 10, 10), -1)
    cv2.imwrite(str(scan_path), img)

    imp_resp = client.post(f"/api/v2/projects/{proj_id}/imports", json={"file_paths": [str(scan_path)]})
    assert imp_resp.status_code == 200
    page_id = imp_resp.json()["pages"][0]["id"]

    r1 = {
        "id": "r1",
        "sequence": 1,
        "geometry": {"type": "rectangle", "x": 100, "y": 100, "width": 400, "height": 400},
        "source": "manual",
        "status": "APPROVED",
        "export": {"archive": True, "clean": True, "vector": True}
    }
    client.post(f"/api/v2/pages/{page_id}/regions", json=r1)

    # Get presets
    presets_resp = client.get("/api/v2/vector/presets")
    assert presets_resp.status_code == 200
    presets = presets_resp.json()
    assert len(presets) == 3

    # Generate preview
    prev_resp = client.post(f"/api/v2/pages/{page_id}/regions/r1/vector-preview", json={
        "preset_id": "historical_bw",
        "custom_params": {"filter_speckle": 2}
    })
    assert prev_resp.status_code == 200
    data = prev_resp.json()
    assert "<svg" in data["svg_content"]
    assert data["path_count"] >= 1
    assert data["elapsed_ms"] > 0


def test_vectorizer_registry(tmp_path):
    from app.vector.registry import vectorizer_registry

    providers = vectorizer_registry.list_providers()
    assert "vtracer" in providers
    assert "potrace" in providers

    # Test vtracer through registry
    vtracer_vec = vectorizer_registry.get("vtracer")
    assert vtracer_vec is not None

    test_png = tmp_path / "test_reg.png"
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    cv2.circle(img, (100, 100), 50, (0, 0, 0), -1)
    cv2.imwrite(str(test_png), img)

    out_svg = tmp_path / "out_reg.svg"
    res = vtracer_vec.vectorize(test_png, out_svg, settings={"colormode": "bw"})
    assert out_svg.exists()
    assert res.path_count >= 1
    assert res.format == "svg"

    # Test potrace fallback through registry
    potrace_vec = vectorizer_registry.get("potrace")
    assert potrace_vec is not None
    out_potrace_svg = tmp_path / "out_potrace.svg"
    res_potrace = potrace_vec.vectorize(test_png, out_potrace_svg)
    assert out_potrace_svg.exists()
    assert res_potrace.path_count >= 1

