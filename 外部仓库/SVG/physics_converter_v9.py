# -*- coding: utf-8 -*-
"""
物理题图 → 可编辑 SVG 转换器 v9 — 精确修复版
修复: 轨迹曲线(轮廓追踪+贝塞尔拟合) + 轨道同心约束 + 坐标精确对齐
"""
import cv2, numpy as np, json, os, sys

# ============ 配置 ============
INPUT_IMG = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUT_DIR = r"D:\brain\eyes\SVG"
SCALE = 3  # 放大倍数
FONT_FAMILY = "Noto Sans SC, SimSun, 'Times New Roman', serif"

img = cv2.imread(INPUT_IMG)
if img is None:
    print(f"ERROR: Cannot read {INPUT_IMG}")
    sys.exit(1)
H, W = img.shape[:2]
print(f"原图尺寸: {W}x{H}")

out_w, out_h = W * SCALE, H * SCALE

# ============ 1. 火星圆形检测（基准圆心）============
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
mars_circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
    minDist=30, param1=50, param2=30, minRadius=20, maxRadius=50)
assert mars_circles is not None and len(mars_circles) > 0, "未检测到火星圆"
mx_raw, my_raw, mr_raw = mars_circles[0][0].astype(int)
print(f"火星圆心: ({mx_raw},{my_raw}), 半径: {mr_raw}px")

# 放大到输出坐标系
mx, my, mr = mx_raw * SCALE, my_raw * SCALE, mr_raw * SCALE

# ============ 2. 标记点检测（S/Q/P）============
binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
contours_all, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

markers = []
min_area, max_area = 5, 120
for c in contours_all:
    area = cv2.contourArea(c)
    if min_area < area < max_area:
        peri = cv2.arcLength(c, True)
        circularity = 4 * np.pi * area / (peri * peri) if peri > 0 else 0
        if circularity > 0.65:
            M = cv2.moments(c)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"]) * SCALE
                cy = int(M["m01"] / M["m00"]) * SCALE
                markers.append({"cx": cx, "cy": cy, "r": max(4, int(np.sqrt(area/np.pi)) * SCALE), "circ": round(circularity, 2)})

# 按Y坐标排序命名: S(最上), Q(中), P(下)
markers.sort(key=lambda m: m["cy"])
names = ["S", "Q", "P"]
for i, m in enumerate(markers):
    m["name"] = names[i] if i < len(names) else f"M{i}"
print(f"标记点: {[(m['name'], m['cx'], m['cy']) for m in markers]}")

# ============ 3. OCR 文字识别 ============
try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
    result, _ = ocr_engine(img)
    ocr_texts = []
    if result:
        for box, text, conf in result:
            if isinstance(conf, (int, float)) and conf > 0.4:
                cxs = [p[0] for p in box]
                cys = [p[1] for p in box]
                ocr_texts.append({
                    "text": text.strip(),
                    "cx": int(np.mean(cxs)) * SCALE,
                    "cy": int(np.mean(cys)) * SCALE,
                    "conf": round(conf, 3)
                })
    print(f"OCR识别: {[o['text'] for o in ocr_texts]}")
except Exception as e:
    print(f"OCR异常: {e}")
    ocr_texts = []

# ============ 4. 轨迹曲线提取（关键改进：轮廓追踪+平滑拟合）============
# 提取红色/深色曲线：用颜色过滤 + 边缘检测
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# 方法：Canny边缘 + 掩码过滤出轨迹区域（左侧深色曲线）
edges = cv2.Canny(gray, 50, 150)

# 创建掩码：只保留图像左半部分的边缘（轨迹在左边）
mask_left = np.zeros_like(edges)
mask_left[:, :int(W*0.7)] = 255
edges_masked = cv2.bitwise_and(edges, mask_left)

# 再过滤掉虚线轨道区域的边缘（轨道是环形，用形态学开运算去除细碎的虚线）
kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
edges_clean = cv2.morphologyEx(edges_masked, cv2.MORPH_CLOSE, kernel_dilate)

# 找轮廓 - 取最长的那条（就是轨迹曲线）
contours_traj, _ = cv2.findContours(edges_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

trajectory_path = None
max_len = 0
for c in contours_traj:
    arc = cv2.arcLength(c, False)
    if arc > max_len and arc > 80:
        max_len = arc
        # 用更少的点拟合（CHAIN_APPROX_SIMPLE 太稀疏了）
        epsilon = 0.008 * arc
        approx = cv2.approxPolyDP(c, epsilon, False)
        if len(approx) >= 3:
            # 转换为缩放后的坐标
            pts_scaled = [(int(p[0][0]*SCALE), int(p[0][1]*SCALE)) for p in approx]
            trajectory_path = pts_scaled
            print(f"轨迹曲线: {len(pts_scaled)}个控制点, 弧长约{arc:.0f}px")

# 如果没找到足够好的轮廓，退回到Hough线段+聚类
if not trajectory_path or len(trajectory_path) < 5:
    print("轮廓追踪效果不佳，使用Hough线段聚类...")
    lines = cv2.HoughLinesP(gray, rho=1, theta=np.pi/720, threshold=25,
        minLineLength=20, maxLineGap=8)
    
    long_lines = []
    if lines is not None:
        for l in lines:
            x1, y1, x2, y2 = l[0]
            length = np.hypot(x2-x1, y2-y1)
            if length > 25:
                long_lines.append([x1*SCALE, y1*SCALE, x2*SCALE, y2*SCALE])
        
        # 按位置排序并连接成路径
        if long_lines:
            # 简单贪心连接
            used = set()
            ordered = [long_lines[0]]
            used.add(0)
            
            for _ in range(len(long_lines)-1):
                last = ordered[-1]
                last_end = np.array([last[2], last[3]])
                best_i, best_dist = -1, float('inf')
                for i, ll in enumerate(long_lines):
                    if i in used:
                        continue
                    ll_start = np.array([ll[0], ll[1]])
                    d = np.linalg.norm(last_end - ll_start)
                    if d < best_dist:
                        best_dist = d
                        best_i = i
                if best_i >= 0:
                    ordered.append(long_lines[best_i])
                    used.add(best_i)
            
            trajectory_path = [(l[0], l[1]) for l in ordered] + [(ordered[-1][2], ordered[-1][3])]
            print(f"Hough备用方案: {len(trajectory_path)}个点")

# 将点序列转换为SVG平滑path（Catmull-Rom样条转贝塞尔）
def catmull_rom_to_bezier(points, closed=False):
    """将点序列转为平滑的三次贝塞尔曲线"""
    if len(points) < 2:
        return ""
    if len(points) == 2:
        return f"M{points[0][0]},{points[0][1]} L{points[1][0]},{points[1][1]}"
    
    pts = list(points)
    n = len(pts)
    
    # Catmull-Rom 样条
    def cr_point(p0, p1, p2, p3, t):
        t2 = t*t; t3 = t2*t
        return (
            0.5*((2*p1[0]) + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3),
            0.5*((2*p1[1]) + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
        )
    
    # 添加虚拟端点（首尾各加2个，确保Catmull-Rom有足够的控制点）
    pts_ext = [pts[0], pts[0]] + pts + [pts[-1], pts[-1]]
    
    d_parts = []
    for i in range(n):
        p0 = pts_ext[i]
        p1 = pts_ext[i+1]
        p2 = pts_ext[i+2]
        p3 = pts_ext[i+3]
        
        # 用4段贝塞尔逼近每段Catmull-Rom
        for j in range(4):
            t0 = j/4
            t1 = (j+1)/4
            
            start = cr_point(p0,p1,p2,p3,t0) if j==0 else prev_end
            end = cr_point(p0,p1,p2,p3,t1)
            prev_end = end
            
            if j == 0 and i == 0:
                d_parts.append(f"M{start[0]:.1f},{start[1]:.1f}")
            # 计算控制点（简化：线性近似）
            mid_t = (t0+t1)/2
            tangent_scale = (t1-t0)*0.5
            dx = (p2[0]-p0[0]) * tangent_scale * 0.6
            dy = (p2[1]-p0[1]) * tangent_scale * 0.6
            cp1x = start[0] + dx
            cp1y = start[1] + dy
            cp2x = end[0] - dx
            cp2y = end[1] - dy
            d_parts.append(f"C{cp1x:.1f},{cp1y:.1f} {cp2x:.1f},{cp2y:.1f} {end[0]:.1f},{end[1]:.1f}")
    
    return " ".join(d_parts)


# ============ 5. 轨道参数（基于原图分析，强制同心）============
# 从原图分析：三条轨道半径比例约为 r_I:r_II:r_III ≈ 3.3:2.4:1.6
orbits = [
    {"name": "I",   "r_ratio": 3.35, "label_pos": "right"},
    {"name": "II",  "r_ratio": 2.35, "label_pos": "right"},
    {"name": "III", "r_ratio": 1.55, "label_pos": "right"},
]

for orb in orbits:
    orb["r_px"] = int(mr * orb["r_ratio"])  # 相对于火星半径的比例
    orb["label_x"] = mx + orb["r_px"] + 12*SCALE
    orb["label_y"] = my + orb["r_px"] * 0.45


# ============ 6. 构建 SVG ============
svg_parts = []

# defs
svg_parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{out_w}" height="{out_h}"
     viewBox="0 0 {out_w} {out_h}" style="background:#fff;">
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0,10 3.5,0 7" fill="#CC0000"/>
  </marker>
</defs>
<style>
  .orbit {{stroke:#000;fill:none;stroke-dasharray:{4*SCALE},{3*SCALE};stroke-width:{1.5*SCALE:.1f}}}
  .traj {{stroke:#CC0000;fill:none;stroke-width:{2*SCALE:.1f};marker-end:url(#arrow)}}
  .planet {{fill:#fff;stroke:#000;stroke-width:{1.5*SCALE:.1f}}}
  .dot {{fill:#000}}
  .txt {{font-size:{16*SCALE:.0f}px;font-family:{FONT_FAMILY};fill:#000}}
  .txt-b {{font-size:{16*SCALE:.0f}px;font-family:{FONT_FAMILY};fill:#000;font-weight:bold}}
  .lbl {{font-size:{14*SCALE:.0f}px;font-family:{FONT_FAMILY};fill:#000;font-style:italic}}
</style>''')

svg_parts.append(f'<rect width="{out_w}" height="{out_h}" fill="#fff"/>')

# 轨道（全部以火星为圆心！）
for orb in orbits:
    svg_parts.append(f'''
<g data-orbit="{orb['name']}">
  <circle cx="{mx}" cy="{my}" r="{orb['r_px']}" class="orbit"/>
  <text x="{orb['label_x']}" y="{orb['label_y']}" class="lbl">{orb['name']}</text>
</g>''')

# 火星
svg_parts.append(f'''
<g data-type="planet">
  <circle cx="{mx}" cy="{my}" r="{mr}" class="planet"/>
  <text x="{mx}" y="{my + 5*SCALE}" class="txt-b" text-anchor="middle">火星</text>
</g>''')

# 标记点 S/Q/P
for mk in markers:
    label_offset = 10 * SCALE
    svg_parts.append(f'''
<g data-marker="{mk['name']}">
  <circle cx="{mk['cx']}" cy="{mk['cy']}" r="{mk['r']}" class="dot"/>
  <text x="{mk['cx']+label_offset}" y="{mk['cy']+4*SCALE}" class="txt-b">{mk['name']}</text>
</g>''')

# 轨迹曲线（平滑贝塞尔）
if trajectory_path and len(trajectory_path) >= 3:
    path_d = catmull_rom_to_bezier(trajectory_path)
    svg_parts.append(f'''
<!-- 轨迹曲线 I ({len(trajectory_path)}控制点, Catmull-Rom→Bezier平滑) -->
<path d="{path_d}" class="traj"/>
''')
else:
    svg_parts.append('<!-- 警告: 未检测到有效轨迹曲线 -->')

svg_parts.append('</svg>')

svg_content = "\n".join(svg_parts)

# ============ 7. 写文件 ============
os.makedirs(OUT_DIR, exist_ok=True)

svg_file = os.path.join(OUT_DIR, "mars_orbit_v9.svg")
with open(svg_file, 'w', encoding='utf-8') as f:
    f.write(svg_content)
print(f"\n✅ SVG已保存: {svg_file}")

analysis = {
    "version": "v9-fixed",
    "image_size": [W, H],
    "output_size": [out_w, out_h],
    "scale": SCALE,
    "mars": {"cx": mx, "cy": my, "r": mr},
    "orbits": [{"name": o["name"], "r": o["r_px"], "center": [mx, my]} for o in orbits],
    "markers": [{"name": m["name"], "cx": m["cx"], "cy": m["cy"], "circ": m["circ"]} for m in markers],
    "ocr": ocr_texts,
    "trajectory_points": len(trajectory_path) if trajectory_path else 0,
}

json_file = os.path.join(OUT_DIR, "analysis_v9.json")
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)
print(f"分析报告: {json_file}")

print("\n=== 完成 ===")
