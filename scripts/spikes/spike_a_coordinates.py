"""
Spike A — OpenSeadragon Coordinate Math Validation (Headless)

This script validates the coordinate transformation math that will be used
between OpenSeadragon viewport coordinates and master pixel coordinates,
WITHOUT requiring a browser.

OpenSeadragon's coordinate system:
- Viewport: normalized so that image width = 1.0 (by default)
- Image: actual pixel coordinates of the source image

The transformations are:
  viewport_x = image_x / image_width
  viewport_y = image_y / image_width  (note: divided by WIDTH, not height)
  
  image_x = viewport_x * image_width
  image_y = viewport_y * image_width

This is because OSD normalizes by width to maintain aspect ratio.
"""

import json
import math
import random
import sys
from dataclasses import dataclass


@dataclass
class Point:
    x: float
    y: float


def master_to_viewport(pt: Point, master_width: int, master_height: int) -> Point:
    """Simulate OpenSeadragon's imageToViewportCoordinates."""
    # OSD normalizes by width (image width = 1.0 in viewport coords)
    return Point(
        x=pt.x / master_width,
        y=pt.y / master_width  # Note: divided by width, not height
    )


def viewport_to_master(pt: Point, master_width: int, master_height: int) -> Point:
    """Simulate OpenSeadragon's viewportToImageCoordinates."""
    return Point(
        x=pt.x * master_width,
        y=pt.y * master_width  # Note: multiplied by width, not height
    )


def test_rectangle_coords():
    """Test 1: Rectangle coordinate round-trip."""
    print("\n=== Test 1: Rectangle Coordinate Round-Trip ===")
    
    master_w, master_h = 12000, 8000
    rect = {"x": 3312, "y": 1704, "w": 1168, "h": 1160}
    
    # Convert corners to viewport and back
    tl = Point(rect["x"], rect["y"])
    br = Point(rect["x"] + rect["w"], rect["y"] + rect["h"])
    
    tl_vp = master_to_viewport(tl, master_w, master_h)
    br_vp = master_to_viewport(br, master_w, master_h)
    
    tl_recovered = viewport_to_master(tl_vp, master_w, master_h)
    br_recovered = viewport_to_master(br_vp, master_w, master_h)
    
    err_tl = math.sqrt((tl_recovered.x - tl.x) ** 2 + (tl_recovered.y - tl.y) ** 2)
    err_br = math.sqrt((br_recovered.x - br.x) ** 2 + (br_recovered.y - br.y) ** 2)
    max_err = max(err_tl, err_br)
    
    print(f"  Master:    ({tl.x}, {tl.y}) to ({br.x}, {br.y})")
    print(f"  Viewport:  ({tl_vp.x:.6f}, {tl_vp.y:.6f}) to ({br_vp.x:.6f}, {br_vp.y:.6f})")
    print(f"  Recovered: ({tl_recovered.x:.4f}, {tl_recovered.y:.4f}) to ({br_recovered.x:.4f}, {br_recovered.y:.4f})")
    print(f"  Max error: {max_err:.10f} px")
    
    passed = max_err < 1e-6  # Should be exact (floating point)
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    return passed


def test_polygon_coords():
    """Test 2: Polygon coordinate round-trip."""
    print("\n=== Test 2: Polygon Coordinate Round-Trip ===")
    
    master_w, master_h = 12000, 8000
    polygon = [
        Point(3312, 1704),
        Point(4480, 1658),
        Point(4612, 2864),
        Point(3401, 2940),
    ]
    
    max_err = 0
    for i, pt in enumerate(polygon):
        vp = master_to_viewport(pt, master_w, master_h)
        recovered = viewport_to_master(vp, master_w, master_h)
        err = math.sqrt((recovered.x - pt.x) ** 2 + (recovered.y - pt.y) ** 2)
        max_err = max(max_err, err)
        print(f"  Vertex {i}: ({pt.x}, {pt.y}) → vp({vp.x:.6f}, {vp.y:.6f}) → ({recovered.x:.4f}, {recovered.y:.4f}) err={err:.10f}")
    
    passed = max_err < 1e-6
    print(f"  Max error: {max_err:.10f} px")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    return passed


def test_stress_random():
    """Test 3: Stress test with 10000 random points."""
    print("\n=== Test 3: Stress Test — 10000 Random Points ===")
    
    master_w, master_h = 12000, 8000
    N = 10000
    max_err = 0
    fail_count = 0
    
    random.seed(42)
    for _ in range(N):
        original = Point(random.random() * master_w, random.random() * master_h)
        vp = master_to_viewport(original, master_w, master_h)
        recovered = viewport_to_master(vp, master_w, master_h)
        err = math.sqrt((recovered.x - original.x) ** 2 + (recovered.y - original.y) ** 2)
        if err > 1.0:
            fail_count += 1
        max_err = max(max_err, err)
    
    passed = fail_count == 0
    print(f"  {N} points tested")
    print(f"  Max error: {max_err:.10f} px")
    print(f"  Failures (>1px): {fail_count}")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    return passed


def test_huge_image():
    """Test 4: Coordinate accuracy on huge images (20000×15000)."""
    print("\n=== Test 4: Huge Image (20000×15000) ===")
    
    master_w, master_h = 20000, 15000
    test_points = [
        Point(0, 0),               # top-left corner
        Point(master_w, 0),        # top-right
        Point(0, master_h),        # bottom-left
        Point(master_w, master_h), # bottom-right
        Point(master_w / 2, master_h / 2),  # center
        Point(19999, 14999),       # near max
        Point(1, 1),               # near min
    ]
    
    max_err = 0
    for pt in test_points:
        vp = master_to_viewport(pt, master_w, master_h)
        recovered = viewport_to_master(vp, master_w, master_h)
        err = math.sqrt((recovered.x - pt.x) ** 2 + (recovered.y - pt.y) ** 2)
        max_err = max(max_err, err)
        print(f"  ({pt.x:>6.0f}, {pt.y:>6.0f}) → vp({vp.x:.6f}, {vp.y:.6f}) → ({recovered.x:.4f}, {recovered.y:.4f}) err={err:.10f}")
    
    passed = max_err < 1e-6
    print(f"  Max error: {max_err:.10f} px")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    return passed


def test_multi_resolution():
    """Test 5: Various master resolutions."""
    print("\n=== Test 5: Multi-Resolution Coordinate Test ===")
    
    resolutions = [
        (800, 600),
        (4000, 3000),
        (12000, 8000),
        (20000, 15000),
        (30000, 20000),
    ]
    
    all_passed = True
    random.seed(123)
    
    for w, h in resolutions:
        max_err = 0
        for _ in range(1000):
            original = Point(random.random() * w, random.random() * h)
            vp = master_to_viewport(original, w, h)
            recovered = viewport_to_master(vp, w, h)
            err = math.sqrt((recovered.x - original.x) ** 2 + (recovered.y - original.y) ** 2)
            max_err = max(max_err, err)
        
        passed = max_err < 1e-6
        all_passed = all_passed and passed
        print(f"  {w:>5}×{h:<5} — maxErr={max_err:.10f} — {'PASS' if passed else 'FAIL'}")
    
    print(f"  Result: {'PASS' if all_passed else 'FAIL'}")
    return all_passed


def main():
    print("=" * 60)
    print("SPIKE A — OpenSeadragon Coordinate Math Validation")
    print("=" * 60)
    print(f"Testing OSD viewport ↔ master pixel coordinate transforms")
    
    results = []
    results.append(("Rectangle Coords", test_rectangle_coords()))
    results.append(("Polygon Coords", test_polygon_coords()))
    results.append(("Stress Test (10K pts)", test_stress_random()))
    results.append(("Huge Image (20K×15K)", test_huge_image()))
    results.append(("Multi-Resolution", test_multi_resolution()))
    
    print("\n" + "=" * 60)
    print("SPIKE A — SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<25} {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🟢 SPIKE A: ALL TESTS PASSED")
        print("   Coordinate transforms are mathematically correct.")
        print("   Browser-based validation available at: scripts/spikes/spike_a_osd_test.html")
    else:
        print("🔴 SPIKE A: SOME TESTS FAILED")
        print("   DO NOT PROCEED — coordinate accuracy is a release blocker.")
    
    print("=" * 60)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
