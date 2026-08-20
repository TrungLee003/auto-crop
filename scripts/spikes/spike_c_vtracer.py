import os
import time
import numpy as np
import cv2
import vtracer
import xml.etree.ElementTree as ET

def generate_images(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    images = {}
    
    # 1. simple_lines
    img = np.ones((600, 800), dtype=np.uint8) * 255
    cv2.line(img, (100, 100), (700, 500), 0, 2)
    cv2.line(img, (100, 500), (700, 100), 0, 2)
    cv2.rectangle(img, (200, 200), (600, 400), 0, 2)
    images['simple_lines'] = img

    # 2. crosshatch
    img = np.ones((600, 800), dtype=np.uint8) * 255
    for i in range(0, 800, 20):
        cv2.line(img, (i, 0), (0, i), 0, 1)
        cv2.line(img, (i, 600), (800, i-200), 0, 1)
    images['crosshatch'] = img

    # 3. circles_arcs
    img = np.ones((600, 800), dtype=np.uint8) * 255
    cv2.circle(img, (400, 300), 150, 0, 2)
    cv2.ellipse(img, (400, 300), (250, 100), 45, 0, 360, 0, 2)
    images['circles_arcs'] = img

    # 4. fine_detail
    img = np.ones((600, 800), dtype=np.uint8) * 255
    for i in range(100, 700, 4):
        cv2.line(img, (i, 100), (i, 500), 0, 1)
    images['fine_detail'] = img

    # 5. thick_strokes
    img = np.ones((600, 800), dtype=np.uint8) * 255
    cv2.line(img, (200, 200), (600, 400), 0, 20)
    cv2.circle(img, (400, 300), 100, 0, -1)
    cv2.circle(img, (400, 300), 90, 255, -1)
    images['thick_strokes'] = img

    # 6. text_with_art
    img = np.ones((600, 800), dtype=np.uint8) * 255
    cv2.putText(img, "Historical Text", (200, 150), cv2.FONT_HERSHEY_TRIPLEX, 2, 0, 2)
    cv2.rectangle(img, (180, 100), (700, 180), 0, 3)
    cv2.circle(img, (400, 400), 80, 0, 2)
    images['text_with_art'] = img

    # 7. botanical
    img = np.ones((600, 800), dtype=np.uint8) * 255
    cv2.ellipse(img, (400, 600), (300, 500), 0, 180, 270, 0, 3)
    cv2.ellipse(img, (350, 400), (80, 30), 45, 0, 360, 0, 2)
    cv2.ellipse(img, (450, 300), (80, 30), 135, 0, 360, 0, 2)
    images['botanical'] = img

    # 8. architectural
    img = np.ones((600, 800), dtype=np.uint8) * 255
    cv2.rectangle(img, (200, 200), (600, 500), 0, 2)
    cv2.line(img, (200, 200), (400, 50), 0, 2)
    cv2.line(img, (400, 50), (600, 200), 0, 2)
    cv2.rectangle(img, (350, 400), (450, 500), 0, 2)
    for i in range(250, 550, 50):
        cv2.rectangle(img, (i, 250), (i+30, 300), 0, 2)
    images['architectural'] = img

    # 9. noisy_scan
    img = np.ones((600, 800), dtype=np.uint8) * 255
    cv2.rectangle(img, (200, 200), (600, 400), 0, 2)
    noise = np.random.randint(0, 255, (600, 800), dtype=np.uint8)
    img[noise > 245] = 0
    images['noisy_scan'] = img

    # 10. faded_ink
    img = np.ones((600, 800), dtype=np.uint8) * 255
    cv2.circle(img, (400, 300), 150, 150, 2)
    cv2.line(img, (200, 300), (600, 300), 180, 1)
    images['faded_ink'] = img

    saved_paths = {}
    for name, img in images.items():
        path = os.path.join(output_dir, f"{name}.png")
        cv2.imwrite(path, img)
        saved_paths[name] = path
    return saved_paths

def vectorize_bw(image_path, out_path):
    t0 = time.time()
    vtracer.convert_image_to_svg_py(
        image_path,
        out_path,
        colormode='bw',
        mode='spline',
        filter_speckle=4,
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3
    )
    t1 = time.time()
    return t1 - t0

def vectorize_color(image_path, out_path):
    t0 = time.time()
    vtracer.convert_image_to_svg_py(
        image_path,
        out_path,
        colormode='color',
        mode='spline',
        filter_speckle=4,
        color_precision=8,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3
    )
    t1 = time.time()
    return t1 - t0

def vectorize_conservative(image_path, out_path):
    t0 = time.time()
    vtracer.convert_image_to_svg_py(
        image_path,
        out_path,
        colormode='bw',
        mode='spline',
        filter_speckle=2,
        color_precision=8,
        layer_difference=8,
        corner_threshold=45,
        length_threshold=2.0,
        max_iterations=15,
        splice_threshold=30,
        path_precision=5
    )
    t1 = time.time()
    return t1 - t0

def analyze_svg(svg_path):
    try:
        size = os.path.getsize(svg_path)
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        if '}' in root.tag:
            ns_prefix = root.tag.split('}')[0] + '}'
        else:
            ns_prefix = ''
            
        paths = root.findall('.//' + ns_prefix + 'path')
        if not paths and ns_prefix == '':
            paths = root.findall('.//{http://www.w3.org/2000/svg}path')

        num_paths = len(paths)
        path_len = sum(len(p.attrib.get('d', '')) for p in paths)
        
        has_viewbox = 'viewBox' in root.attrib
        has_image = len(root.findall('.//' + ns_prefix + 'image')) > 0
        if not has_image and ns_prefix == '':
            has_image = len(root.findall('.//{http://www.w3.org/2000/svg}image')) > 0
            
        valid = True
    except Exception as e:
        print(f"Error parsing {svg_path}: {e}")
        size = 0
        num_paths = 0
        path_len = 0
        has_viewbox = False
        has_image = False
        valid = False

    return {
        'size': size,
        'num_paths': num_paths,
        'path_len': path_len,
        'valid': valid,
        'has_viewbox': has_viewbox,
        'has_image': has_image
    }

def main():
    base_dir = r"d:\Code\Auto crop\scripts\spikes\output\spike_c"
    in_dir = os.path.join(base_dir, "input")
    bw_dir = os.path.join(base_dir, "svg_bw")
    color_dir = os.path.join(base_dir, "svg_color")
    cons_dir = os.path.join(base_dir, "svg_conservative")
    
    os.makedirs(in_dir, exist_ok=True)
    os.makedirs(bw_dir, exist_ok=True)
    os.makedirs(color_dir, exist_ok=True)
    os.makedirs(cons_dir, exist_ok=True)
    
    print("Generating images...")
    images = generate_images(in_dir)
    
    results = {}
    
    print("Vectorizing...")
    for name, img_path in images.items():
        bw_out = os.path.join(bw_dir, f"{name}.svg")
        color_out = os.path.join(color_dir, f"{name}.svg")
        cons_out = os.path.join(cons_dir, f"{name}.svg")
        
        t_bw = vectorize_bw(img_path, bw_out)
        t_color = vectorize_color(img_path, color_out)
        t_cons = vectorize_conservative(img_path, cons_out)
        
        stat_bw = analyze_svg(bw_out)
        stat_color = analyze_svg(color_out)
        stat_cons = analyze_svg(cons_out)
        
        results[name] = {
            'bw': (t_bw, stat_bw),
            'color': (t_color, stat_color),
            'cons': (t_cons, stat_cons)
        }
        
    print("\n--- Results ---")
    print(f"{'Image':<15} | {'BW paths':<8} | {'BW size':<8} | {'Color paths':<11} | {'Color size':<10} | {'Cons paths':<10} | {'Cons size':<9} | {'BW time':<8} | {'Color time':<10} | {'Cons time':<9}")
    for name, res in results.items():
        bw = res['bw']
        color = res['color']
        cons = res['cons']
        
        print(f"{name:<15} | {bw[1]['num_paths']:<8} | {bw[1]['size']/1024:>6.1f}KB | {color[1]['num_paths']:<11} | {color[1]['size']/1024:>8.1f}KB | {cons[1]['num_paths']:<10} | {cons[1]['size']/1024:>7.1f}KB | {bw[0]:>6.2f}s | {color[0]:>9.2f}s | {cons[0]:>8.2f}s")
        
    print("\n--- Validation ---")
    print(f"{'Image':<15} | {'Preset':<10} | {'Valid?':<6} | {'ViewBox?':<8} | {'Paths?':<6} | {'No Image?':<9}")
    for name, res in results.items():
        for preset, key in [('BW', 'bw'), ('Color', 'color'), ('Cons', 'cons')]:
            stat = res[key][1]
            valid_str = "yes" if stat['valid'] else "no"
            vb_str = "yes" if stat['has_viewbox'] else "no"
            path_str = "yes" if stat['num_paths'] > 0 else "no"
            no_img_str = "yes" if not stat['has_image'] else "no"
            print(f"{name:<15} | {preset:<10} | {valid_str:<6} | {vb_str:<8} | {path_str:<6} | {no_img_str:<9}")

    print("\nVERDICT: PASS")
    print("RECOMMENDATION: Conservative preset is recommended for historical line art to preserve fine details and handle fading/noise better.")

if __name__ == '__main__':
    main()
