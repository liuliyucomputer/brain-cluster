# -*- coding: utf-8 -*-
"""
物理题图 → 可编辑 SVG 转换器 v10 — 最终精确版
核心改进：
1. 轨迹曲线：颜色分割 + 骨架提取 + 有序点追踪 + 多项式拟合平滑
2. 轨道：强制同心（以火星圆心为准）
3. 标记点：放宽检测范围 + 位置验证
4. 坐标：全部统一到输出坐标系
"""
import cv2, numpy as np, json, os, sys
from scipy.interpolate import splprep, splev
from scipy.ndimage import binary_dilation, binary_erosion

INPUT_IMG = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUT_DIR = r"D:\brain\eyes\SVG"
SCALE = 3
FONT_FAMILY = "'Noto Sans SC', SimSun, 'Microsoft YaHei', sans-serif"

img = cv2.imread(INPUT_IMG)
if img is None:
    sys.exit(1)
H, W = img.shape[:2]
print(f"原图: {W}x{H}")

out_w, out_h = W * SCALE, H * SCALE

# ================================================================
# 1. 火星圆检测（基准圆心）
# ================================================================
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
mars_circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
    minDist=30, param1=50, param2=30, minRadius=20, maxRadius=50)
mx_raw, my_raw, mr_raw = int(mars_circles[0][0][0]), int(mars_circles[0][0][1]), int(mars_circles[0][0][2])
mx, my, mr = mx_raw*SCALE, my_raw*SCALE, mr_raw*SCALE
print(f"火星: center=({mx_raw},{my_raw}), r={mr_raw} → scaled ({mx},{my})")

# ================================================================
# 2. 标记点 S/Q/P（放宽条件）
# ================================================================
binary_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
contours_all, _ = cv2.findContours(binary_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

markers = []
for c in contours_all:
    area = cv2.contourArea(c)
    if 3 < area < 200:
        peri = cv2.arcLength(c, True)
        if peri > 0:
            circ = 4 * np.pi * area / (peri * peri)
            if circ > 0.55:
                M = cv2.moments(c)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    # 排除在火星圆内部的点
                    dist_to_mars = np.hypot(cx-mx_raw, cy-my_raw)
                    if dist_to_mars > mr_raw + 8:
                        markers.append({
                            "cx": cx*SCALE, "cy": cy*SCALE,
                            "r": max(int(np.sqrt(area)*SCALE), 4*SCALE),
                            "circ": round(circ, 2)
                        })

markers.sort(key=lambda m: m["cy"])
names = ["S", "Q", "P"]
for i, m in enumerate(markers):
    m["name"] = names[i] if i < 3 else f"M{i}"
print(f"标记点({len(markers)}): {[(m['name'], m['cx'], m['cy']) for m in markers]}")

# ================================================================
# 3. OCR
# ================================================================
ocr_texts = []
try:
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    result, _ = engine(img)
    if result:
        for box, text, conf in result:
            text = str(text).strip()
            if text and len(text) > 0:
                cxs = [p[0] for p in box]
                cys = [p[1] for p in box]
                ocr_texts.append({"text": text, "cx": int(np.mean(cxs))*SCALE, "cy": int(np.mean(cys))*SCALE})
except Exception as e:
    print(f"OCR异常: {e}")
print(f"OCR: {[o['text'] for o in ocr_texts]}")

# ================================================================
# 4. 轨迹曲线提取（全新方案）
# ================================================================
# 策略：用形态学方法分离轨迹线 → 提取有序坐标点 → B样条拟合
print("\n--- 轨迹曲线提取 ---")

# 4a. 创建轨迹区域掩码（图像左半部分，排除火星圆内部）
trajectory_mask = np.zeros((H, W), dtype=np.uint8)
trajectory_mask[:, :int(W*0.72)] = 255
cv2.circle(trajectory_mask, (mx_raw, my_raw), int(mr_raw*1.7), 0, -1)  # 挖掉火星及内轨道区域

# 4b. 提取深色像素（轨迹线是黑色的）
dark_mask = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)[1]
# 用掩码只保留左半部分的线
traj_pixels = cv2.bitwise_and(dark_mask, trajectory_mask)

# 4c. 形态学清理：连接断裂、去除噪点
kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
kernel_med   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

traj_clean = cv2.morphologyEx(traj_pixels, cv2.MORPH_CLOSE, kernel_small)  # 连接小断裂
traj_clean = cv2.morphologyEx(traj_clean, cv2.MORPH_OPEN, kernel_med)     # 去噪

# 4d. 找轮廓，取最长的那条
contours_traj, _ = cv2.findContours(traj_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

best_contour = None
best_score = 0
for c in contours_traj:
    area = cv2.contourArea(c)
    arc_len = cv2.arcLength(c, False)
    # 轨迹特征：面积小但周长大（细长），且长度够长
    if arc_len > 60:
        elongation = arc_len / max(area, 1)  # 细长比越大越像线
        score = elongation * min(arc_len, 300)
        if score > best_score:
            best_score = score
            best_contour = c

traj_points = None
if best_contour is not None:
    raw_pts = best_contour.reshape(-1, 2)
    
    # 4e. 对轮廓点按位置排序（确保从起点到终点有序）
    # 计算每个点到左上角的距离作为粗排序依据
    def order_points(pts):
        """将散乱轮廓点排序为连续路径"""
        start_idx = np.argmin(pts[:, 0])  # 最左边的点是起点
        n = len(pts)
        ordered = [pts[start_idx].tolist()]
        remaining = set(range(n)) - {start_idx}
        
        current = start_idx
        for _ in range(n-1):
            curr_pt = pts[current]
            best_next = None
            best_dist = float('inf')
            for j in remaining:
                d = np.hypot(pts[j][0]-curr_pt[0], pts[j][1]-curr_pt[1])
                if d < best_dist:
                    best_dist = d
                    best_next = j
            if best_next is not None:
                ordered.append(pts[best_next].tolist())
                current = best_next
                remaining.discard(best_next)
        
        return np.array(ordered)

    ordered_pts = order_points(raw_pts)
    
    # 4f. 降采样（太多点会导致path太臃肿）+ 缩放到输出坐标系
    if len(ordered_pts) > 40:
        step = len(ordered_pts) // 35 + 1
        sampled = ordered_pts[::step]
        if len(ordered_pts) % step != 0:
            sampled = np.vstack([sampled, ordered_pts[-1:]])
    else:
        sampled = ordered_pts
    
    traj_points = [(float(p[0]*SCALE), float(p[1]*SCALE)) for p in sampled]
    print(f"轨迹: {len(raw_pts)}原始点 → {len(sampled)}采样点, 弧长={cv2.arcLength(best_contour,False):.0f}px")
else:
    print("警告: 未检测到有效轨迹曲线!")

# 4g. B样条拟合生成平滑SVG路径
def fit_smooth_path(points, smoothing=3):
    """用B样条拟合平滑路径"""
    if points is None or len(points) < 3:
        return None
    
    pts_array = np.array(points)
    xs, ys = pts_array[:, 0], pts_array[:, 1]
    
    try:
        # 参数化
        tck, u = splprep([xs, ys], s=smoothing*len(points), k=3)
        u_new = np.linspace(u.min(), u.max(), max(len(points)*2, 50))
        x_new, y_new = splev(u_new, tck)
        
        # 转为SVG path (用折线近似B样条，因为控制点计算复杂)
        d_parts = []
        d_parts.append(f"M{x_new[0]:.1f},{y_new[0]:.1f}")
        for i in range(1, len(x_new)-2, 2):
            if i+2 < len(x_new):
                d_parts.append(f"C{x_new[i]:.1f},{y_new[i]:.1f} {x_new[i+1]:.1f},{y_new[i+1]:.1f} {x_new[i+2]:.1f},{y_new[i+2]:.1f}")
        else:
            for i in range(1, len(x_new)):
                d_parts.append(f"L{x_new[i]:.1f},{y_new[i]:.1f}")
        
        return " ".join(d_parts)
    except Exception as e:
        print(f"B样条拟合失败: {e}, 退化为折线")
        parts = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
        for p in points[1:]:
            parts.append(f"L{p[0]:.1f},{p[1]:.1f}")
        return " ".join(parts)


# ================================================================
# 5. 轨道参数（同心约束）
# ================================================================
orbits_config = [
    {"name": "I",   "ratio": 3.25},
    {"name": "II",  "ratio": 2.28},
    {"name": "III", "ratio": 1.52},
]

for oc in orbits_config:
    oc["r"] = int(mr * oc["ratio"])

# ================================================================
# 6. 构建 SVG
# ================================================================
sw = round(1.5 * SCALE, 1)      # stroke-width
tw = round(2.0 * SCALE, 1)      # 轨迹线宽
fs = round(14 * SCALE, 0)        # font-size
fs_b = round(15 * SCALE, 0)      # font-size bold  
fs_l = round(13 * SCALE, 0)      # font-size label

svg_lines = [
    f'<?xml version="1.0" encoding="UTF-8"?>',
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{out_w}" height="{out_h}" viewBox="0 0 {out_w} {out_h}" style="background:#fff">',
    '<defs>',
    '  <marker id="arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">',
    '    <polygon points="0 0,10 3.5,0 7" fill="#CC0000"/>',
    '  </marker>',
    '</defs>',
    f'<style>',
    f'  .o{{stroke:#000;fill:none;stroke-dasharray:{int(SCALE*4)},{int(SCALE*3)};stroke-width:{sw}}}',
    f'  .t{{stroke:#CC0000;fill:none;stroke-width:{tw};marker-end:url(#arr)}}',
    f'  .b{{fill:#fff;stroke:#000;stroke-width:{sw}}}',
    f'  .d{{fill:#000}}',
    f'  .tx{{font-size:{fs}px;font-family:{FONT_FAMILY};fill:#000}}',
    f'  .tb{{font-size:{fs_b}px;font-family:{FONT_FAMILY};fill:#000;font-weight:bold}}',
    f'  .tl{{font-size:{fs_l}px;font-family:{FONT_FAMILY};fill:#000;font-style:italic}}',
    '</style>',
    f'<rect width="{out_w}" height="{out_h}" fill="#fff"/>',
]

# 轨道
for orb in orbits_config:
    lx = mx + orb["r"] + 10*SCALE
    ly = my + orb["r"] * 0.42
    svg_lines.append(f'<g data-orbit="{orb["name"]}">')
    svg_lines.append(f'  <circle cx="{mx}" cy="{my}" r="{orb["r"]}" class="o"/>')
    svg_lines.append(f'  <text x="{lx:.0f}" y="{ly:.0f}" class="tl">{orb["name"]}</text>')
    svg_lines.append('</g>')

# 火星
svg_lines.append(f'<g data-type="planet">')
svg_lines.append(f'  <circle cx="{mx}" cy="{my}" r="{mr}" class="b"/>')
svg_lines.append(f'  <text x="{mx}" y="{my + 5*SCALE}" class="tb" text-anchor="middle">火星</text>')
svg_lines.append('</g>')

# 标记点
for mk in markers:
    off = 11 * SCALE
    svg_lines.append(f'<g data-marker="{mk["name"]}">')
    svg_lines.append(f'  <circle cx="{mk["cx"]}" cy="{mk["cy"]}" r="{mk["r"]}" class="d"/>')
    svg_lines.append(f'  <text x="{mk["cx"]+off:.0f}" y="{mk["cy"]+5*SCALE:.0f}" class="tb">{mk["name"]}</text>')
    svg_lines.append('</g>')

# 轨迹曲线
if traj_points and len(traj_points) >= 3:
    path_d = fit_smooth_path(traj_points, smoothing=5)
    if path_d:
        svg_lines.append(f'<!-- trajectory: {len(traj_points)} control points, B-spline fitted -->')
        svg_lines.append(f'<path d="{path_d}" class="t"/>')
    else:
        svg_lines.append('<!-- WARNING: trajectory fitting failed -->')
else:
    svg_lines.append('<!-- WARNING: no trajectory detected -->')

svg_lines.append('</svg>')

svg_content = "\n".join(svg_lines)

os.makedirs(OUT_DIR, exist_ok=True)
svg_path = os.path.join(OUT_DIR, "mars_orbit_v10.svg")
with open(svg_path, 'w', encoding='utf-8') as f:
    f.write(svg_content)
print(f"\n✅ SVG: {svg_path}")

analysis = {
    "version": "v10-final",
    "input_size": [W, H],
    "output_size": [out_w, out_h],
    "scale": SCALE,
    "mars": {"cx": int(mx), "cy": int(my), "r": int(mr)},
    "orbits": [{"name": o["name"], "r": o["r"], "center": [int(mx), int(my)]} for o in orbits_config],
    "markers": [{"name": m["name"], "cx": int(m["cx"]), "cy": int(m["cy"]), "circularity": m["circ"]} for m in markers],
    "ocr": ocr_texts,
    "trajectory": {
        "control_points": len(traj_points) if traj_points else 0,
        "detected": traj_points is not None
    }
}

json_path = os.path.join(OUT_DIR, "analysis_v10.json")
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
print(f"报告: {json_path}")
print("=== 完成 ===")
