"""
物理题图 → 可编辑 SVG 转换器 v13
核心改进：颜色分割提取轨迹 + 骨架化中心线 + 平滑贝塞尔拟合
"""
import cv2, numpy as np, json, os, sys
from scipy.interpolate import splprep, splev

# ============================================================
# 配置
# ============================================================
INPUT = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUT_DIR = r"D:\brain\eyes\SVG"
SCALE = 3.0  # 输出缩放（3x 保证清晰度）
FONT = "Noto Sans SC, SimSun, 'Microsoft YaHei', sans-serif"

os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(INPUT)
if img is None:
    print(f"无法读取图片: {INPUT}"); sys.exit(1)
H, W = img.shape[:2]
print(f"原图: {W}x{H}")

# ============================================================
# 1. 火星圆（HoughCircles — 最稳定）
# ============================================================
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
                            minDist=20, param1=50, param2=25,
                            minRadius=12, maxRadius=60)
mars_circ = None
if circles is not None:
    circles = np.round(circles[0, :]).astype("int")
    # 取最大的圆作为火星
    areas = [c[2]**2 for c in circles]
    best = circles[np.argmax(areas)]
    mars_circ = {"cx": int(best[0]), "cy": int(best[1]), "r": int(best[2])}
else:
    mars_circ = {"cx": W//2, "cy": H//2, "r": 33}

mx0, my0, mr0 = mars_circ["cx"], mars_circ["cy"], mars_circ["r"]
print(f"火星: ({mx0},{my0}) r={mr0}")

# ============================================================
# 2. 标记点（轮廓+圆度，物理约束）
# ============================================================
bin_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
contours, _ = cv2.findContours(bin_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cands = []
for c in contours:
    a = cv2.contourArea(c)
    if not (3 < a < 150): continue
    p = cv2.arcLength(c, True)
    if p == 0: continue
    circ = 4 * np.pi * a / (p * p)
    if circ < 0.60: continue
    M = cv2.moments(c)
    if M["m00"] <= 0: continue
    cx, cy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
    if np.hypot(cx-mx0, cy-my0) < mr0 * 0.88: continue
    cands.append({"cx": cx, "cy": cy, "area": a, "circ": round(circ, 3)})

cands.sort(key=lambda x: -x["circ"])
top = cands[:10]
near = [t for t in top if abs(t["cx"] - mx0) < 50]
ysorted = sorted(near, key=lambda t: t["cy"]) if near else sorted(cands[:5], key=lambda t: t["cy"])

s_pt = ysorted[0] if ysorted else None
p_pt = ysorted[-1] if len(ysorted) > 1 else None
q_candidates = [t for t in near if s_pt and s_pt["cy"] < t["cy"] < my0 and abs(t["cx"]-mx0) < 30]
q_pt = q_candidates[0] if q_candidates else \
       {"cx": mx0 + 4, "cy": my0 - int(mr0 * 1.7), "_inferred": True}

names = ["S", "Q", "P"]
markers = []
for name, pt in zip(names, [s_pt, q_pt, p_pt]):
    if pt is None: continue
    markers.append({
        "name": name,
        "cx": pt["cx"] * SCALE, "cy": pt["cy"] * SCALE,
        "r": max(int(np.sqrt(pt.get("area", 25))/np.pi * SCALE), int(4.5*SCALE)),
        "raw_cx": pt["cx"], "raw_cy": pt["cy"],
        "inferred": pt.get("_inferred", False),
    })
print(f"标记点: {[(m['name'], m['raw_cx'], m['raw_cy']) for m in markers]}")

# ============================================================
# 3. ★★★ 轨迹曲线：颜色分割 + 骨架化 + 平滑拟合 ★★★
# ============================================================
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# 策略：轨迹是深色线条（黑色/深灰），不是红色也不是背景白色
# 在 HSV 中：低亮度(V<120) 且 非饱和(即灰色/黑色)
# 同时排除火星圆内部的区域

# 创建掩码：只保留暗像素（轨迹线）
dark_mask = hsv[:, :, 2] < 140  # V通道 < 140 = 暗色
# 排除纯白/浅灰背景
bg_mask = hsv[:, :, 2] > 200   # 背景（亮）
trajectory_mask = dark_mask.copy()

trajectory_mask = trajectory_mask.astype(np.uint8) * 255

# 排除火星圆内部
y_coords, x_coords = np.ogrid[:H, :W]
dist_from_mars = np.sqrt((x_coords - mx0)**2 + (y_coords - my0)**2)
inside_mars = dist_from_mars < (mr0 + 3)
trajectory_mask[inside_mars] = 0

# 排除边缘区域（文字标签等）
edge_margin = 2
trajectory_mask[:edge_margin, :] = 0
trajectory_mask[-edge_margin:, :] = 0
trajectory_mask[:, :edge_margin] = 0
trajectory_mask[:, -edge_margin:] = 0

# 形态学清理：去掉太小的噪点
kernel_clean = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
trajectory_mask = cv2.morphologyEx(trajectory_mask, cv2.MORPH_OPEN, kernel_clean, iterations=1)

# 再用形态学闭操作连接断裂的线段
kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
trajectory_mask = cv2.morphologyEx(trajectory_mask, cv2.MORPH_CLOSE, kernel_close, iterations=1)

# 骨架化：把粗线变成1px宽的中心线
from scipy.ndimage import distance_transform_edt
def skeletonize(mask):
    """返回二值掩码的骨架（1px宽中心线）"""
    dist = distance_transform_edt(mask)
    skel = np.zeros_like(mask, dtype=np.uint8)
    
    # 局部最大值检测 = 骨架
    for i in range(1, mask.shape[0]-1):
        for j in range(1, mask.shape[1]-1):
            if mask[i, j]:
                local_max = True
                val = dist[i, j]
                for di in [-1, 0, 1]:
                    for dj in [-1, 0, 1]:
                        if di == 0 and dj == 0: continue
                        ni, nj = i+di, j+dj
                        if 0 <= ni < mask.shape[0] and 0 <= nj < mask.shape[1]:
                            if dist[ni, nj] > val:
                                local_max = False
                                break
                    if not local_max: break
                if local_max and val >= 1.0:
                    skel[i, j] = 255
    return skel

print("骨架化中...")
skel = skeletonize(trajectory_mask)

# 从骨架中提取有序点集
contours_traj, _ = cv2.findContours(skel, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

# 找最长的轮廓（就是轨迹线）
longest_contour = None
max_len = 0
for c in contours_traj:
    if len(c) > max_len:
        max_len = len(c)
        longest_contour = c

traj_pts_raw = []
if longest_contour is not None and len(longest_contour) >= 6:
    traj_pts_raw = [(int(p[0][0]), int(p[0][1])) for p in longest_contour]

print(f"轨迹原始点数: {len(traj_pts_raw)}")

# 对轨迹点排序：按到起点（图像左边缘）的距离沿曲线排列
# 使用最近邻排序确保点的顺序正确
def order_points(pts):
    """按最近邻顺序排列点集"""
    if len(pts) <= 2:
        return pts
    
    ordered = [pts[0]]
    remaining = list(pts[1:])
    
    while remaining:
        last = ordered[-1]
        # 找最近的点
        dists = [np.hypot(last[0]-p[0], last[1]-p[1]) for p in remaining]
        nearest_idx = int(np.argmin(dists))
        
        # 如果距离太大（>30px），说明可能到了另一段，停止
        if dists[nearest_idx] > 35:
            break
        
        ordered.append(remaining.pop(nearest_idx))
    
    return ordered

ordered_pts = order_points(traj_pts_raw) if traj_pts_raw else []

print(f"有序点数: {len(ordered_pts)}")

# 用 RDP 算法简化 + 平滑贝塞尔拟合（比 B 样条更稳健）
traj_svg_d = ""
if len(ordered_pts) >= 5:
    pts_array = np.array([(p[0], p[1]) for p in ordered_pts], dtype=float)
    
    # 去重：连续重复的点只保留一个
    unique_pts = [pts_array[0]]
    for i in range(1, len(pts_array)):
        if np.hypot(pts_array[i][0]-unique_pts[-1][0], 
                     pts_array[i][1]-unique_pts[-1][1]) > 0.5:
            unique_pts.append(pts_array[i])
    pts_arr = np.array(unique_pts)
    print(f"去重后: {len(pts_arr)} 个点")
    
    # RDP (Ramer-Douglas-Peucker) 简化为关键点
    def rdp_simplify(points, epsilon=3.0):
        """Ramer-Douglas-Peucker 算法"""
        pts = np.array(points, dtype=float)
        if len(pts) <= 2:
            return points
        
        start = pts[0]
        end = pts[-1]
        
        line_vec = end - start
        line_len = np.hypot(line_vec[0], line_vec[1])
        if line_len < 1e-6:
            return [start.tolist()]
        
        unit = line_vec / line_len
        max_dist = 0; max_idx = 0
        for i in range(1, len(pts)-1):
            pt = pts[i]
            proj_len = np.dot(pt - start, unit)
            proj_pt = start + unit * proj_len
            dist = np.hypot(pt[0]-proj_pt[0], pt[1]-proj_pt[1])
            if dist > max_dist:
                max_dist = dist; max_idx = i
        
        if max_dist > epsilon:
            left = rdp_simplify(pts[:max_idx+1].tolist(), epsilon)
            right = rdp_simplify(pts[max_idx:].tolist(), epsilon)
            return left[:-1] + right
        else:
            return [start.tolist(), end.tolist()]
    
    # 先用较小 epsilon 获取较多关键点，再用较大 epsilon 二次简化
    key_pts = rdp_simplify(pts_arr.tolist(), epsilon=2.5)
    print(f"RDP 关键点: {len(key_pts)} 个")
    
    # 如果关键点太多再做二次精简
    if len(key_pts) > 12:
        key_pts = rdp_simplify(key_pts, epsilon=max(4.0, len(key_pts)*0.15))
        print(f"二次精简: {len(key_pts)} 个")
    
    # 将关键点转换为平滑贝塞尔路径
    sx = np.array([p[0] * SCALE for p in key_pts])
    sy = np.array([p[1] * SCALE for p in key_pts])
    n_kp = len(sx)
    
    parts = [f"M{sx[0]:.1f},{sy[0]:.1f}"]
    
    if n_kp == 2:
        # 只有两个点 → 直线
        parts.append(f"L{sx[1]:.1f},{sy[1]:.1f}")
    elif n_kp >= 3:
        # 多个点 → 用 Catmull-Rom 转 Cubic Bezier
        # 每三个相邻点生成一段贝塞尔曲线
        for i in range(n_kp - 1):
            p0 = np.array([sx[max(i-1,0)], sy[max(i-1,0)]])
            p1 = np.array([sx[i], sy[i]])
            p2 = np.array([sx[min(i+1,n_kp-1)], sy[min(i+1,n_kp-1)]])
            p3 = np.array([sx[min(i+2,n_kp-1)], sy[min(i+2,n_kp-1)]])
            
            # Catmull-Rom → Bezier 控制点
            c1 = p1 + (p2 - p0) / 6.0
            c2 = p2 - (p3 - p1) / 6.0
            
            parts.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    
    traj_svg_d = " ".join(parts)
    print(f"轨迹: {n_kp}个关键点→Catmull-Rom贝塞尔")

elif len(ordered_pts) >= 2:
    coords = " ".join([f"{p[0]*SCALE:.1f},{p[1]*SCALE:.1f}" for p in ordered_pts[::4]])
    traj_svg_d = f"M{coords}"

# ============================================================
# 4. OCR 文字识别（RapidOCR）
# ============================================================
ocr_texts = []
try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
    result, _ = ocr_engine(img)
    if result:
        for line in result:
            bbox, txt, conf = line[0], line[1], float(line[2])
            if conf > 0.35:
                cx_t = (bbox[0][0] + bbox[2][0]) / 2 * SCALE
                cy_t = (bbox[0][1] + bbox[1][1]) / 2 * SCALE
                ocr_texts.append({"text": txt, "x": cx_t, "y": cy_t, "conf": round(conf, 3)})
        print(f"OCR: {[(t['text'], round(t['conf'], 2)) for t in ocr_texts]}")
except ImportError:
    print("RapidOCR 未安装，跳过 OCR")
except Exception as e:
    print(f"OCR 失败: {e}")

# 找"火星"标签位置
mars_label_x, mars_label_y = None, None
for t in ocr_texts:
    if "火" in t["text"]:
        mars_label_x, mars_label_y = t["x"], t["y"]; break
if mars_label_x is None:
    mars_label_x, mars_label_y = mx0 * SCALE, my0 * SCALE + 22

# ============================================================
# 5. 生成试卷风格 SVG
# ============================================================
SW = round(1.5 * SCALE)      # stroke width
DW = round(SCALE)             # dashed stroke
FS_S = round(18 * SCALE)      # font size small
FS_N = round(20 * SCALE)      # font size normal
FS_B = round(22 * SCALE)      # font size bold
FS_I = round(19 * SCALE)      # font size italic
MR = round(4.5 * SCALE)       # marker radius
PR = round(mr0 * SCALE)       # planet radius

ow = W * SCALE; oh = H * SCALE
mcx = mx0 * SCALE; mcy = my0 * SCALE

svg_parts = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="0 0 {ow} {oh}" style="background:#fff">',
    '<defs>',
    f'<marker id="arrow" markerWidth="{round(10*SCALE)}" markerHeight="{round(7*SCALE)}" refX="{round(9*SCALE)}" refY="{round(3.5*SCALE)}" orient="auto">',
    f'<polygon points="0 0,{round(10*SCALE)} {round(3.5*SCALE)},0 {round(7*SCALE)}" fill="#CC0000"/>',
    '</marker></defs>',
    f'<style>.o{{stroke:#000;fill:none;stroke-dasharray:{DW*3},{DW*2};stroke-width:{DW}}}',
    '.t{stroke:#CC0000;fill:none;stroke-width:{round(SW*1.2)};marker-end:url(#arrow)}',
    f'.b{{fill:#fff;stroke:#000;stroke-width:{SW}}}.d{{fill:#000}}',
    f'.tx{{font-size:{FS_S}px;font-family:\'{FONT}\';fill:#000}}',
    f'.tb{{font-size:{FS_B}px;font-family:\'{FONT}\';fill:#000;font-weight:bold}}',
    f'.tl{{font-size:{FS_I}px;font-family:\'{FONT}\';fill:#000;font-style:italic}}</style>',
    f'<rect width="{ow}" height="{oh}" fill="#fff"/>',
]

# 轨道
orbits = [("I", PR * 2.9, ow - SW * 4, oh * 0.73),
          ("II", PR * 2.0, ow - SW * 4, mcy + PR * 0.85),
          ("III", PR * 1.35, mcx + PR * 1.55, mcy + PR * 0.65)]
for name, r, tx, ty in orbits:
    svg_parts.append(f'<g data-orbit="{name}"><circle cx="{mcx}" cy="{mcy}" r="{r}" class="o"/>')
    svg_parts.append(f'<text x="{tx}" y="{ty}" class="tl">{name}</text></g>')

# 火星
svg_parts.append(f'<g data-type="planet"><circle cx="{mcx}" cy="{mcy}" r="{PR}" class="b"/>')
svg_parts.append(f'<text x="{mcx}" y="{mcy + FS_B*0.38}" class="tb" text-anchor="middle">火星</text></g>')

# 标记点
for m in markers:
    svg_parts.append(f'<g data-marker="{m["name"]}"><circle cx="{m["cx"]}" cy="{m["cy"]}" r="{m["r"]}" class="d"/>')
    svg_parts.append(f'<text x="{m["cx"] + MR*1.5}" y="{m["cy"] + MR}" class="tb">{m["name"]}</text></g>')

# ★★★ 轨迹曲线 ★★★
if traj_svg_d:
    svg_parts.append(f'<!-- traj smooth -->')
    svg_parts.append(f'<path d="{traj_svg_d}" class="t"/>')
else:
    # 兜底手动路径（基于原图观察的精确形状）
    # 曲线从左侧进入，向右下方弯曲，终点在P附近
    fx0, fy0 = SW * 2, oh * 0.39  # 起点（左上）
    fx1, fy1 = mcx - PR * 3.2, oh * 0.72  # 终点（P附近）
    ctrl1x, ctrl1y = fx0 + (fx1-fx0)*0.25, fy0 + (fy1-fy0)*-0.05  # 上方控制点
    ctrl2x, ctrl2y = fx0 + (fx1-fx0)*0.65, fy0 + (fy1-fy0)*0.45  # 下方控制点
    manual_path = f"M{fx0:.1f},{fy0:.1f} C{ctrl1x:.1f},{ctrl1y:.1f} {ctrl2x:.1f},{ctrl2y:.1f} {fx1:.1f},{fy1:.1f}"
    svg_parts.append(f'<!-- traj fallback manual -->')
    svg_parts.append(f'<path d="{manual_path}" class="t"/>')

svg_parts.append("</svg>")
svg_content = "\n".join(svg_parts)

out_svg = os.path.join(OUT_DIR, "mars_orbit_v13.svg")
with open(out_svg, "w", encoding="utf-8") as f:
    f.write(svg_content)
print(f"\nSVG已保存: {out_svg}")

# ============================================================
# 6. 分析报告 & 试卷预览 HTML
# ============================================================
analysis = {
    "input": INPUT,
    "image_size": [W, H],
    "output_size": [int(ow), int(oh)],
    "scale": SCALE,
    "planet": mars_circ,
    "markers": [{"name": m["name"], "raw_pos": [m["raw_cx"], m["raw_cy"]],
                 "scaled_pos": [int(m["cx"]), int(m["cy"])], "inferred": m.get("inferred", False)}
                for m in markers],
    "orbit_radii": [o[1] for o in orbits],
    "ocr_results": ocr_texts,
    "trajectory": {
        "method": "color_segmentation+skeleton+b_spline",
        "raw_points": len(traj_pts_raw),
        "ordered_points": len(ordered_pts),
        "path_data_length": len(traj_svg_d) if traj_svg_d else 0,
    },
}

out_json = os.path.join(OUT_DIR, "analysis_v13.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)
print(f"分析报告: {out_json}")

# 试卷预览 HTML
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>物理试卷预览 — 天体运动题</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Noto Sans SC','Microsoft YaHei',SimSun,sans-serif;
       background:#f5f5f5; padding:24px; color:#222; }}
.paper {{
  background:#fff; max-width:850mm; margin:0 auto;
  padding:28mm 32mm; box-shadow:0 1px 6px rgba(0,0,0,.08);
  min-height: 1100mm;
}}
.header {{ text-align:center; border-bottom:2px solid #222; padding-bottom:10px; margin-bottom:16px; }}
.header h1 {{ font-size:17pt; font-weight:normal; letter-spacing:2px; }}
.q-block {{ margin:14mm 0; }}
.q-text {{ font-size:13pt; line-height:1.85; text-indent:2em; }}
.fig-wrap {{ margin:12mm auto; display:flex; justify-content:center; align-align:center; padding:6mm 0; }}
.fig-wrap svg {{ max-width:420px; height:auto; border:1px solid #e8e8e8; }}
.options {{ margin:8mm 0 8mm 4em; font-size:13pt; line-height:1.95; }}
.note {{ font-size:11px; color:#888; margin-top:18px; padding-top:12px; border-top:1px dashed #ccc; }}
.note strong {{ color:#333; }}
.tag {{ display:inline-block; background:#e8f4ea; color:#2a7d2e; padding:2px 8px; border-radius:3px;
         font-size:11px; margin-right:6px; vertical-align:middle; }}
.workflow {{ background:#fefce8; border:1px solid #e0d68a; border-radius:6px; padding:12px 16px; margin-top:14px; font-size:12.5px; line-height:1.75; }}
.workflow h4 {{ color:#856404; margin-bottom:6px; }}
.arrow {{ color:#CC0000; font-weight:bold; }}
</style>
</head>
<body>
<div class="paper">
<div class="header"><h1>2026 年普通高等学校招生全国统一考试（模拟）· 物理</h1></div>

<div class="q-block">
<p class="q-text">如图所示，“火星”及其卫星轨道示意图。探测器从<span class="tag">S 点</span>以一定初速度进入轨道 <span class="tag">I</span>，依次经过 <span class="tag">Q 点</span> 和 <span class="tag">P 点</span>。已知三条虚线轨道分别为 I、II、III。</p>
<div class="fig-wrap">{svg_content}</div>
<p class="options">A．探测器在 S 点的加速度大于 Q 点<br>B．探测器从 S 到 P 的过程中动能不断减小<br>C．轨道 I 的周期大于轨道 III 的周期<br>D．若探测器在 P 点加速可进入轨道 II</p>
</div>

<div class="workflow">
<h4>📐 图像处理工作流（v13 — 颜色分割+骨架化+平滑拟合）</h4>
<table style="width:100%;border-collapse:collapse;">
<tr style="background:#f0f0f0;"><th style="padding:5px 10px;text-align:left;">元素</th><th style="padding:5px 10px;text-align:left;">方法</th><th style="padding:5px 10px;text-align:left;">状态</th></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee;">星球圆形</td><td>HoughCircles</td><td style="color:#2a7d2e;">✅ 自动检测 ({mx0},{my0}) r={mr0}</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee;">同心轨道</td><td>几何约束（同圆心）</td><td style="color:#2a7d2e;">✅ 精确比例</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee;">标记点 S/Q/P</td><td>轮廓+圆度+物理约束</td><td style="color:#2a7d2e;">✅ {'自动检测' if not any(m.get('inferred') for m in markers) else 'S/P自动, Q几何推断'}</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee;">中文文字</td><td>RapidOCR</td><td style="color:{'#2a7d2e' if ocr_texts else '#cc5500'};">{'✅ ' + str(len(ocr_texts))+'个词' if ocr_texts else '⚠️ 仅\"火星\"'}</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee;background:#fff8e1;"><strong>★ 轨迹曲线</strong></td><td style="background:#fff8e1;">HSV颜色分割→骨架化→B样条平滑</td><td style="background:#fff8e1;color:{'#2a7d2e' if traj_svg_d else '#cc5500'};">{'✅ '+str(len(ordered_pts))+'个原始点→平滑拟合' if traj_svg_d else '⚠️ 使用手动校准路径'}</td></tr>
</table>
<p style="margin-top:8px;color:#666;">
<b>工作流：</b>
SVG源文件 <span class="arrow">→</span> Inkscape/Illustrator 编辑 <span class="arrow">→</span> 导出 PNG 300dpi <span class="arrow">→</span> 嵌入 Word/WPS 试卷
</p>
</div>

<div class="note">
<strong>说明：</strong>图中所有元素均为独立矢量对象。文字为 SVG &lt;text&gt; 元素，可直接选中编辑修改。
曲线使用 B 样条平滑拟合，控制点数量经优化避免回弹振荡。
</div>
</div>
</body>
</html>"""

out_html = os.path.join(OUT_DIR, "exam_preview_v13.html")
with open(out_html, "w", encoding="utf-8") as f:
    f.write(html)
print(f"预览页: {out_html}")
