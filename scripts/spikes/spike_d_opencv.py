import cv2
import numpy as np
import os
import time

OUTPUT_IN = r"d:\Code\Auto crop\scripts\spikes\output\spike_d\input"
OUTPUT_RES = r"d:\Code\Auto crop\scripts\spikes\output\spike_d\results"
os.makedirs(OUTPUT_IN, exist_ok=True)
os.makedirs(OUTPUT_RES, exist_ok=True)

def generate_pages():
    pages = {}
    gt = {}
    
    # 1. Sparse page (2 well-separated illustrations with drawing contents)
    sparse = np.full((2500, 3500, 3), 255, dtype=np.uint8)
    cv2.rectangle(sparse, (500, 500), (1500, 1000), (30, 30, 30), 4)
    for x in range(550, 1450, 40):
        cv2.line(sparse, (x, 520), (x+20, 980), (40, 40, 40), 2)
    cv2.rectangle(sparse, (2000, 1200), (3000, 2000), (30, 30, 30), 4)
    cv2.circle(sparse, (2500, 1600), 300, (40, 40, 40), 3)
    pages['sparse_page'] = sparse
    gt['sparse_page'] = [(500, 500, 1000, 500), (2000, 1200, 1000, 800)] # x, y, w, h
    
    # 2. Dense page (5 illustrations)
    dense = np.full((2500, 3500, 3), 255, dtype=np.uint8)
    rects = [
        (100, 100, 600, 400),
        (850, 150, 500, 500),
        (100, 700, 1200, 700),
        (1600, 200, 1700, 1000),
        (500, 1600, 1000, 700)
    ]
    for x, y, w, h in rects:
        cv2.rectangle(dense, (x, y), (x+w, y+h), (30, 30, 30), 3)
        cv2.line(dense, (x, y), (x+w, y+h), (40, 40, 40), 2)
        cv2.line(dense, (x+w, y), (x, y+h), (40, 40, 40), 2)
    pages['dense_page'] = dense
    gt['dense_page'] = rects
    
    # 3. Text heavy page (lots of small text lines, plus 2 distinct illustration blocks)
    text_heavy = np.full((2500, 3500, 3), 255, dtype=np.uint8)
    for i in range(200, 2300, 40):
        cv2.rectangle(text_heavy, (300, i), (3200, i+8), (100, 100, 100), -1)
    rects_text = [(500, 400, 800, 600), (2000, 1400, 1000, 800)]
    for x, y, w, h in rects_text:
        cv2.rectangle(text_heavy, (x, y), (x+w, y+h), (255, 255, 255), -1)
        cv2.rectangle(text_heavy, (x, y), (x+w, y+h), (20, 20, 20), 4)
        cv2.circle(text_heavy, (x+w//2, y+h//2), min(w, h)//3, (30, 30, 30), 3)
    pages['text_heavy_page'] = text_heavy
    gt['text_heavy_page'] = rects_text
    
    # 4. Degraded page (aged yellow/noisy background)
    degraded = np.full((2500, 3500, 3), (210, 230, 245), dtype=np.uint8)
    noise = np.random.normal(0, 12, degraded.shape).astype(np.int16)
    degraded = np.clip(degraded.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    rects_deg = [(400, 400, 1000, 800), (2200, 500, 800, 1200)]
    for x, y, w, h in rects_deg:
        cv2.rectangle(degraded, (x, y), (x+w, y+h), (40, 30, 20), 4)
        for d in range(50, min(w, h)//2, 40):
            cv2.circle(degraded, (x+w//2, y+h//2), d, (50, 40, 30), 2)
    pages['degraded_page'] = degraded
    gt['degraded_page'] = rects_deg
    
    # 5. Mixed page
    mixed = np.full((2500, 3500, 3), 255, dtype=np.uint8)
    rects_mix = [(200, 200, 1000, 500), (300, 800, 800, 600), (2000, 1000, 1200, 1200), (2500, 200, 500, 500)]
    for x, y, w, h in rects_mix:
        cv2.rectangle(mixed, (x, y), (x+w, y+h), (30, 30, 30), 3)
        cv2.line(mixed, (x, y+h//2), (x+w, y+h//2), (40, 40, 40), 2)
    pages['mixed_page'] = mixed
    gt['mixed_page'] = rects_mix
    
    for name, img in pages.items():
        cv2.imwrite(os.path.join(OUTPUT_IN, f"{name}.png"), img)
        
    return pages, gt

def detection_pipeline(image, profile="historical_line_art"):
    img_h, img_w = image.shape[:2]
    target_long = 3500.0
    scale = target_long / max(img_w, img_h)
    new_w = int(round(img_w * scale))
    new_h = int(round(img_h * scale))
    
    if scale != 1.0:
        working_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        working_img = image.copy()
    
    # 1. Grayscale
    if len(working_img.shape) == 3:
        gray = cv2.cvtColor(working_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = working_img.copy()
        
    # 2. Background Normalization
    kernel_bg = cv2.getStructuringElement(cv2.MORPH_RECT, (51, 51))
    background = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel_bg)
    diff = cv2.absdiff(background, gray)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    
    # 3. Ink Mask
    _, ink_mask = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 4. Noise filtering & stroke consolidation
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    clean_mask = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN, kernel_small)
    
    # Connect strokes within illustration
    kernel_connect = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
    grouped_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel_connect)
    
    # 5. Connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(grouped_mask, connectivity=8)
    
    # 6. Filter components
    min_area = 500
    max_area = int(0.90 * (new_w * new_h))
    
    candidate_boxes = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area < min_area or area > max_area:
            continue
        # Filter full-page horizontal text stripes
        aspect_ratio = w / float(h) if h > 0 else 0
        if aspect_ratio > 20.0 and h < 30:
            continue
        candidate_boxes.append([x, y, x + w, y + h])
        
    # 7. Spatial Clustering
    def merge_boxes(boxes, max_dist=30):
        if not boxes:
            return []
        merged = []
        for box in boxes:
            x1, y1, x2, y2 = box
            merged_into = False
            for i, m in enumerate(merged):
                mx1, my1, mx2, my2 = m
                if not (x2 + max_dist < mx1 or x1 - max_dist > mx2 or y2 + max_dist < my1 or y1 - max_dist > my2):
                    merged[i] = [min(mx1, x1), min(my1, y1), max(mx2, x2), max(my2, y2)]
                    merged_into = True
                    break
            if not merged_into:
                merged.append([x1, y1, x2, y2])
        return merged

    merged = merge_boxes(candidate_boxes, max_dist=30)
    
    # 8. Scale back to master coordinates
    final_rects = []
    for m in merged:
        box_x = int(round(m[0] / scale))
        box_y = int(round(m[1] / scale))
        box_w = int(round((m[2] - m[0]) / scale))
        box_h = int(round((m[3] - m[1]) / scale))
        
        box_x = max(0, min(img_w - 1, box_x))
        box_y = max(0, min(img_h - 1, box_y))
        box_w = min(box_w, img_w - box_x)
        box_h = min(box_h, img_h - box_y)
        
        if box_w >= 100 and box_h >= 100:
            final_rects.append((box_x, box_y, box_w, box_h))
        
    return final_rects

def calculate_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0]+boxA[2], boxB[0]+boxB[2])
    yB = min(boxA[1]+boxA[3], boxB[1]+boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]
    unionArea = float(boxAArea + boxBArea - interArea)
    if unionArea == 0:
        return 0.0
    return interArea / unionArea

def evaluate():
    pages, gt = generate_pages()
    print("=" * 65)
    print("SPIKE D — OpenCV Detection Pipeline Validation")
    print("=" * 65)
    print(f"{'Page':<20} {'Time(s)':<10} {'Recall':<10} {'Precision':<10} {'Avg IoU':<10}")
    print("-" * 65)
    
    all_recalls = []
    all_precisions = []
    all_ious = []
    
    for name, img in pages.items():
        t0 = time.time()
        preds = detection_pipeline(img)
        t1 = time.time()
        
        annotated = img.copy()
        for p in preds:
            cv2.rectangle(annotated, (p[0], p[1]), (p[0]+p[2], p[1]+p[3]), (0, 0, 255), 6)
        cv2.imwrite(os.path.join(OUTPUT_RES, f"{name}_res.png"), annotated)
        
        true_pos = 0
        ious = []
        for g in gt[name]:
            best_iou = 0
            for p in preds:
                iou = calculate_iou(g, p)
                if iou > best_iou:
                    best_iou = iou
            if best_iou >= 0.5:
                true_pos += 1
                ious.append(best_iou)
                
        recall = true_pos / len(gt[name]) if len(gt[name]) > 0 else 1.0
        precision = true_pos / len(preds) if len(preds) > 0 else 0.0
        avg_iou = sum(ious) / len(ious) if len(ious) > 0 else 0.0
        
        all_recalls.append(recall)
        all_precisions.append(precision)
        if ious:
            all_ious.extend(ious)
            
        print(f"{name:<20} {t1-t0:<10.3f} {recall:<10.2f} {precision:<10.2f} {avg_iou:<10.2f}")
        
    print("-" * 65)
    mean_recall = sum(all_recalls) / len(all_recalls)
    mean_precision = sum(all_precisions) / len(all_precisions)
    mean_iou = sum(all_ious) / len(all_ious) if all_ious else 0.0
    print(f"{'MEAN':<20} {'-':<10} {mean_recall:<10.2f} {mean_precision:<10.2f} {mean_iou:<10.2f}")
    
    # Coordinate scaling test
    print("\n--- Coordinate Scaling Test ---")
    img = np.full((1200, 800, 3), 255, np.uint8)
    cv2.rectangle(img, (150, 200), (650, 900), (30, 30, 30), 4) # x=150, y=200, w=500, h=700
    cv2.line(img, (150, 200), (650, 900), (40, 40, 40), 2)
    preds = detection_pipeline(img)
    if preds:
        p = preds[0]
        err_x = abs(p[0] - 150)
        err_y = abs(p[1] - 200)
        err_w = abs(p[2] - 500)
        err_h = abs(p[3] - 700)
        max_err = max(err_x, err_y, err_w, err_h)
        # Tolerance for CV bounding box of a 4px stroke after downscaling/upscaling
        pass_scale = max_err <= 5
        print(f"  Target: (150, 200, 500, 700) -> Detected: {p}, max error: {max_err}px")
        print(f"  Scaling Test: {'✅ PASS' if pass_scale else '❌ FAIL'}")
    else:
        print("  Scaling Test: ❌ FAIL (no candidate found)")

    print("=" * 65)

if __name__ == '__main__':
    evaluate()
