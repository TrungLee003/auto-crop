import os
import pytest
from pathlib import Path
import app # triggers dll discovery

def test_pyvips_core_operations(tmp_path):
    import pyvips
    # Create test image
    img = pyvips.Image.black(1000, 1000) + 255
    img = img.bandjoin([img, img])
    
    # Save & load
    out_tif = tmp_path / "test.tif"
    img.tiffsave(str(out_tif))
    assert out_tif.exists()
    
    loaded = pyvips.Image.new_from_file(str(out_tif))
    assert loaded.width == 1000
    assert loaded.height == 1000
    
    # Crop
    crop = loaded.crop(100, 100, 200, 200)
    assert crop.width == 200
    assert crop.height == 200

def test_vtracer_core_operations(tmp_path):
    import vtracer
    import cv2
    import numpy as np
    
    # Create simple drawing
    img = np.full((200, 200), 255, dtype=np.uint8)
    cv2.line(img, (20, 20), (180, 180), 0, 3)
    
    in_png = tmp_path / "art.png"
    out_svg = tmp_path / "art.svg"
    cv2.imwrite(str(in_png), img)
    
    vtracer.convert_image_to_svg_py(str(in_png), str(out_svg), colormode="bw")
    assert out_svg.exists()
    svg_content = out_svg.read_text(encoding="utf-8")
    assert "<svg" in svg_content
    assert "<path" in svg_content
    assert "<image" not in svg_content

def test_opencv_core_processing():
    import cv2
    import numpy as np
    
    img = np.full((500, 500, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (300, 300), (0, 0, 0), -1)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assert len(contours) == 1
    x, y, w, h = cv2.boundingRect(contours[0])
    assert abs(x - 100) <= 2
    assert abs(y - 100) <= 2
    assert abs(w - 200) <= 2
    assert abs(h - 200) <= 2
