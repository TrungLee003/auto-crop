import os
import sys
from pathlib import Path

# Auto-configure Windows libvips binary path
vips_bin = Path(r"d:\Code\Auto crop\backend\vendor\vips-dev-8.18\bin")
if vips_bin.exists():
    os.environ["PATH"] = str(vips_bin) + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(vips_bin))
        except Exception:
            pass

import pyvips
import time
import shutil

OUTPUT_DIR = r"d:\Code\Auto crop\scripts\spikes\output\spike_b"
os.makedirs(OUTPUT_DIR, exist_ok=True)
DZI_DIR = os.path.join(OUTPUT_DIR, "deepzoom")
os.makedirs(DZI_DIR, exist_ok=True)

def run_tests():
    print("=" * 65)
    print("SPIKE B — pyvips Image Pipeline Validation")
    print("=" * 65)
    results = {}

    # B1. Create large test image (12000 x 8000)
    print("\n--- B1: High-Resolution Test Image (12000 x 8000) ---")
    t0 = time.time()
    width, height = 12000, 8000
    
    # White background (RGB)
    bg = pyvips.Image.black(width, height) + 255
    bg = bg.bandjoin([bg, bg]) # 3 bands RGB
    
    # Draw illustration rectangles
    rect1 = (pyvips.Image.black(2000, 1500) + [220, 50, 50]).cast("uchar")
    rect2 = (pyvips.Image.black(3000, 2500) + [50, 180, 50]).cast("uchar")
    rect3 = (pyvips.Image.black(1000, 4000) + [50, 50, 220]).cast("uchar")

    image = bg.insert(rect1, 1000, 1000)
    image = image.insert(rect2, 4000, 2000)
    image = image.insert(rect3, 8000, 3000)

    # 300 DPI metadata (pixels per millimeter in libvips)
    xres = 300.0 / 25.4
    yres = 300.0 / 25.4
    image = image.copy(xres=xres, yres=yres)

    tiff_path = os.path.join(OUTPUT_DIR, "test_image.tif")
    png_path = os.path.join(OUTPUT_DIR, "test_image.png")
    
    image.tiffsave(tiff_path, compression="deflate")
    image.pngsave(png_path)
    t1 = time.time()
    
    tiff_size = os.path.getsize(tiff_path) / (1024 * 1024)
    png_size = os.path.getsize(png_path) / (1024 * 1024)
    
    print(f"  Dimensions: {width} x {height} (96 MP)")
    print(f"  TIFF saved: {tiff_size:.2f} MB")
    print(f"  PNG saved:  {png_size:.2f} MB")
    print(f"  Time:       {t1 - t0:.2f}s")
    results['B1 - Large Master Image'] = 'PASS'

    # B2. Generate DeepZoom pyramid
    print("\n--- B2: DeepZoom (DZI) Generation ---")
    t0 = time.time()
    dzi_base = os.path.join(DZI_DIR, "page_001")
    image.dzsave(dzi_base)
    t1 = time.time()
    
    files_count = 0
    total_size = 0
    files_dir = dzi_base + "_files"
    if os.path.exists(files_dir):
        for root, dirs, files in os.walk(files_dir):
            for f in files:
                files_count += 1
                total_size += os.path.getsize(os.path.join(root, f))
            
    print(f"  DZI generated: {dzi_base}.dzi")
    print(f"  Tiles generated: {files_count} files ({total_size / (1024 * 1024):.2f} MB)")
    print(f"  Time:            {t1 - t0:.2f}s")
    results['B2 - DeepZoom Pyramid'] = 'PASS' if files_count > 0 else 'FAIL'

    # B3. Crop native-resolution rectangles
    print("\n--- B3: Native-Resolution Region Cropping ---")
    t0 = time.time()
    c1 = image.crop(1000, 1000, 2000, 1500)
    c2 = image.crop(4000, 2000, 3000, 2500)
    c3 = image.crop(8000, 3000, 1000, 4000)
    
    c1_path = os.path.join(OUTPUT_DIR, "crop1.png")
    c2_path = os.path.join(OUTPUT_DIR, "crop2.png")
    c3_path = os.path.join(OUTPUT_DIR, "crop3.png")
    c1.pngsave(c1_path)
    c2.pngsave(c2_path)
    c3.pngsave(c3_path)
    t1 = time.time()
    
    c1_ok = (c1.width == 2000 and c1.height == 1500)
    c2_ok = (c2.width == 3000 and c2.height == 2500)
    c3_ok = (c3.width == 1000 and c3.height == 4000)
    
    print(f"  Crop 1: {c1.width}x{c1.height} -> {'OK' if c1_ok else 'FAIL'}")
    print(f"  Crop 2: {c2.width}x{c2.height} -> {'OK' if c2_ok else 'FAIL'}")
    print(f"  Crop 3: {c3.width}x{c3.height} -> {'OK' if c3_ok else 'FAIL'}")
    print(f"  Time:   {t1 - t0:.2f}s")
    results['B3 - Native Res Cropping'] = 'PASS' if (c1_ok and c2_ok and c3_ok) else 'FAIL'

    # B4. Metadata preservation
    print("\n--- B4: Metadata Preservation ---")
    img_load = pyvips.Image.new_from_file(tiff_path)
    res_diff = abs(img_load.xres - xres)
    meta_ok = (res_diff < 0.1 and img_load.width == width and img_load.height == height)
    print(f"  Resolution X: {img_load.xres * 25.4:.1f} DPI (expected 300.0)")
    print(f"  Resolution Y: {img_load.yres * 25.4:.1f} DPI (expected 300.0)")
    print(f"  Width/Height: {img_load.width} x {img_load.height}")
    print(f"  Bands:        {img_load.bands}")
    results['B4 - Metadata Preservation'] = 'PASS' if meta_ok else 'FAIL'
        
    # B5. Huge image stress test (20000 x 15000 = 300 MP)
    print("\n--- B5: Stress Test (20000 x 15000 = 300 MP) ---")
    t0 = time.time()
    w_large, h_large = 20000, 15000
    large_bg = pyvips.Image.black(w_large, h_large) + 255
    large_image = large_bg.bandjoin([large_bg, large_bg])
    
    large_dzi = os.path.join(DZI_DIR, "large_image")
    large_image.dzsave(large_dzi)
    
    l_crop = large_image.crop(10000, 7500, 1500, 1500)
    l_crop_path = os.path.join(OUTPUT_DIR, "large_crop.png")
    l_crop.pngsave(l_crop_path)
    t1 = time.time()
    
    large_ok = os.path.exists(large_dzi + ".dzi") and os.path.exists(l_crop_path)
    print(f"  300 MP image processed in {t1 - t0:.2f}s")
    print(f"  Large DZI generated: {large_dzi}.dzi")
    print(f"  Large crop generated: {l_crop_path}")
    results['B5 - 300MP Stress Test'] = 'PASS' if large_ok else 'FAIL'

    # Summary
    print("\n" + "=" * 65)
    print("SPIKE B — SUMMARY")
    print("=" * 65)
    all_pass = True
    for test_name, status in results.items():
        pass_symbol = "✅ PASS" if status == "PASS" else "❌ FAIL"
        print(f"  {test_name:<35} {pass_symbol}")
        if status != "PASS":
            all_pass = False
            
    print()
    if all_pass:
        print("🟢 SPIKE B: ALL TESTS PASSED")
        print("   pyvips is verified for high-resolution processing and DeepZoom tile generation.")
    else:
        print("🔴 SPIKE B: SOME TESTS FAILED")
    print("=" * 65)

if __name__ == '__main__':
    run_tests()
