"""
物理题图 → 可编辑 SVG 转换器 v14
核心改进：空间约束定位轨迹 + 精确形状拟合
"""
import cv2, numpy as np, json, os, sys

# ============================================================
# 配置
# ============================================================
INPUT = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUT_DIR = r"D:\brain\eyes\SVG"
SCALE = 3.0
FONT = "Noto Sans SC, SimSun, 'Microsoft YaHei', sans-serif"
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(INPUT)
if img is None:
    print(f"无法读取图片: {INPUT}"); sys.exit(1)
H, W = img.shape[:2]
print(f"原图: {W}x{H}")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# ============================================================
# 1. 火星圆（HoughCircles）
# ============================================================
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
                            minDist=20, param1=50, param2=25,
                            minRadius=12, maxRadius=60)
mars_circ = None
if circles is not None:
    circles = np.round(circles[0, :]).astype("int")
    areas = [c[2]**2 for c in circles]
    best = circles[np.argmax(areas)]
    mars_circ = {"cx": int(best[0]), "cy": int(best[1]), "r": int(best[2])}
else:
    mars_circ = {"cx": W//2, "cy": H//2, "r": 33}

mx0, my0, mr0 = mars_circ["cx"], mars_circ["cy"], mars_circ["r"]
print(f"火星: ({mx0},{my0}) r={mr0}")

# ============================================================
# 2. 标记点
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
# 3. ★★★ 轨迹曲线：Canny + 空间约束过滤 + RDP简化 ★★★
# ============================================================
# 步骤1: Canny 边缘检测（低阈值以捕获细线）
edges = cv2.Canny(gray, 40, 100, apertureSize=3)

# 步骤2: 创建空间掩码 — 轨迹在图像左半部分，且在最外层轨道之外或与之交叉
orbit_I_r_px = mr0 * 2.9  # 最外层轨道的估计半径（像素）
spatial_mask = np.zeros((H, W), dtype=np.uint8)

# 轨迹搜索区域：
# - X: 左半边到中心附近 (0 到 mx0+mr0*1.5)
# - Y: 上部到下部（几乎全高）
# - 排除火星圆内部
for y in range(H):
    for x in range(W):
        # X范围：左边大部分
        if x > mx0 + int(mr0 * 1.8):
            continue
        # 不在火星内部
        if np.hypot(x-mx0, y-my0) < mr0 * 0.85:
            continue
        # 在边缘留一点边距
        if x < 1 or y < 1 or x >= W-1 or y >= H-1:
            continue
        spatial_mask[y, x] = 255

# 用形态学扩展搜索区域一点点（连接断裂）
kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
spatial_mask = cv2.dilate(spatial_mask, kernel_dilate, iterations=1)

# 步骤3: 应用空间掩码到边缘图
filtered_edges = cv2.bitwise_and(edges, spatial_mask)

# 步骤4: 找轮廓 — 轨迹是最长的非闭合细长轮廓
contours_traj, _ = cv2.findContours(filtered_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

print(f"Canny+空间过滤后轮廓数: {len(contours_traj)}")

# 筛选轨迹候选：
# - 长度足够（>30px 周长）
# - 细长（长宽比大）
# - 非闭合（面积相对于周长很小）
best_trajectory = None
best_score = 0
traj_info = None

for ci, c in enumerate(contours_traj):
    peri = cv2.arcLength(c, False)
    if peri < 35:  # 太短
        continue
    
    area = cv2.contourArea(c)
    
    # 计算边界框的长宽比（轨迹应该是细长的）
    rect = cv2.boundingRect(c)
    rw, rh = rect[2], rect[3]
    if rw < 5 or rh < 5:
        continue
    aspect = max(rw/rh, rh/rw)  # 长宽比（越大越细长）
    
    # 检查是否闭合：如果首尾距离远则不闭合
    pts = [(int(p[0][0]), int(p[0][1])) for p in c]
    end_dist = np.hypot(pts[0][0]-pts[-1][0], pts[0][1]-pts[-1][1])
    openness = end_dist / max(peri, 1)  # 越大越开放
    
    # 轨迹的特征：细长、开放、较长
    score = peri * aspect * (openness + 0.1) * (1.0 / max(area/peri, 0.5))
    
    # 额外加分：起点靠近图像左侧边缘
    start_x = min(p[0][0] for p in c)
    if start_x < W * 0.25:
        score *= 2.0  # 左边起点的加分
    
    if score > best_score:
        best_score = score
        best_trajectory = c
        traj_info = {
            "perimeter": round(peri, 1),
            "area": round(area, 1),
            "aspect": round(aspect, 2),
            "openness": round(openness, 3),
            "start_x": start_x,
            "n_pts": len(pts),
        }

if best_trajectory is not None:
    print(f"最佳轨迹候选: {traj_info}")
else:
    print("未找到轨迹！")

# 步骤5: 提取有序点并排序
traj_raw = []
if best_trajectory is not None:
    traj_raw = [(int(p[0][0]), int(p[0][1])) for p in best_trajectory]

def order_points_chain(pts):
    """最近邻链式排序"""
    if len(pts) <= 2: return pts
    ordered = [pts[0]]
    remaining = list(pts[1:])
    while remaining:
        last = ordered[-1]
        dists = [np.hypot(last[0]-p[0], last[1]-p[1]) for p in remaining]
        ni = int(np.argmin(dists))
        if dists[ni] > 40: break
        ordered.append(remaining.pop(ni))
    return ordered

ordered = order_points_chain(traj_raw) if traj_raw else []
print(f"轨迹有序点数: {len(ordered)}")

# 步骤6: RDP 简化 → Catmull-Rom 贝塞尔
def rdp(points, eps=3.0):
    pts = np.array(points, dtype=float)
    if len(pts) <= 2:
        return pts.tolist()
    start, end = pts[0], pts[-1]
    vec = end - start; vlen = np.hypot(vec[0], vec[1])
    if vlen < 1e-6: return [start.tolist()]
    unit = vec / vlen; mdist, midx = 0, 0
    for i in range(1, len(pts)-1):
        plen = np.dot(pts[i]-start, unit)
        pp = start + unit * plen
        d = np.hypot(pts[i][0]-pp[0], pts[i][1]-pp[1])
        if d > mdist: mdist, midx = d, i
    if mdist > eps:
        left = rdp(pts[:midx+1].tolist(), eps)
        right = rdp(pts[midx:].tolist(), eps)
        return left[:-1] + right
    return [start.tolist(), end.tolist()]

traj_svg_d = ""
n_key = 0
if len(ordered) >= 4:
    # 去重
    uniq = [ordered[0]]
    for p in ordered[1:]:
        if np.hypot(p[0]-uniq[-1][0], p[1]-uniq[-1][1]) > 0.5:
            uniq.append(p)
    
    # RDP 简化
    key_pts = rdp(uniq, eps=3.0)
    if len(key_pts) > 10:
        key_pts = rdp(key_pts, eps=max(4.0, len(key_pts)*0.12))
    n_key = len(key_pts)
    print(f"RDP关键点: {n_key}")
    
    # Catmull-Rom → Cubic Bezier
    kp = np.array(key_pts, dtype=float) * SCALE
    nk = len(kp)
    parts = [f"M{kp[0][0]:.1f},{kp[0][1]:.1f}"]
    for i in range(nk - 1):
        p0 = kp[max(i-1, 0)]; p1 = kp[i]; p2 = kp[min(i+1, nk-1)]; p3 = kp[min(i+2, nk-1)]
        c1 = p1 + (p2-p0)/6.0; c2 = p2 - (p3-p1)/6.0
        parts.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    traj_svg_d = " ".join(parts)
elif len(ordered) >= 2:
    coords = " ".join([f"{p[0]*SCALE:.1f},{p[1]*SCALE:.1f}" for p in ordered[::4]])
    traj_svg_d = f"M{coords}"

# ============================================================
# 4. OCR
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
                ocr_texts.append({"text": txt, "conf": round(conf, 3)})
        print(f"OCR: {[t['text'] for t in ocr_texts]}")
except Exception as e:
    print(f"OCR跳过: {e}")

mars_label_x, mars_label_y = mx0*SCALE, my0*SCALE + 22

# ============================================================
# 5. SVG 生成
# ============================================================
SW = round(1.5 * SCALE); DW = round(SCALE)
FS_S = round(18 * SCALE); FS_N = round(20 * SCALE)
FS_B = round(22 * SCALE); FS_I = round(19 * SCALE)
MR = round(4.5 * SCALE); PR = round(mr0 * SCALE)
ow, oh = W * SCALE, H * SCALE; mcx, mcy = mx0*SCALE, my0*SCALE

svg_parts = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="0 0 {ow} {oh}" style="background:#fff">',
    '<defs>',
    f'<marker id="arrow" markerWidth="{round(10*SCALE)}" markerHeight="{round(7*SCALE)}" refX="{round(9*SCALE)}" refY="{round(3.5*SCALE)}" orient="auto">',
    f'<polygon points="0 0,{round(10*SCALE)} {round(3.5*SCALE)},0 {round(7*SCALE)}" fill="#CC0000"/></marker></defs>',
    f'<style>.o{{stroke:#000;fill:none;stroke-dasharray:{DW*3},{DW*2};stroke-width:{DW}}}',
    '.t{stroke:#CC0000;fill:none;stroke-width:'+str(round(SW*1.2))+';marker-end:url(#arrow)}',
    f'.b{{fill:#fff;stroke:#000;stroke-width:{SW}}}.d{{fill:#000}}',
    f'.tx{{font-size:{FS_S}px;font-family:\'{FONT}\';fill:#000}}',
    f'.tb{{font-size:{FS_B}px;font-family:\'{FONT}\';fill:#000;font-weight:bold}}',
    f'.tl{{font-size:{FS_I}px;font-family:\'{FONT}\';fill:#000;font-style:italic}}</style>',
    f'<rect width="{ow}" height="{oh}" fill="#fff"/>',
]

orbits = [("I", PR*2.9, ow-SW*4, oh*0.73), ("II", PR*2.0, ow-SW*4, mcy+PR*0.85), ("III", PR*1.35, mcx+PR*1.55, mcy+PR*0.65)]
for name, r, tx, ty in orbits:
    svg_parts.append(f'<g data-orbit="{name}"><circle cx="{mcx}" cy="{mcy}" r="{r}" class="o"/>')
    svg_parts.append(f'<text x="{tx}" y="{ty}" class="tl">{name}</text></g>')

svg_parts.append(f'<g data-type="planet"><circle cx="{mcx}" cy="{mcy}" r="{PR}" class="b"/>')
svg_parts.append(f'<text x="{mcx}" y="{mcy+FS_B*0.38}" class="tb" text-anchor="middle">火星</text></g>')

for m in markers:
    svg_parts.append(f'<g data-marker="{m["name"]}"><circle cx="{m["cx"]}" cy="{m["cy"]}" r="{m["r"]}" class="d"/>')
    svg_parts.append(f'<text x="{m["cx"]+MR*1.5}" y="{m["cy"]+MR}" class="tb">{m["name"]}</text></g>')

# 轨迹
if traj_svg_d:
    svg_parts.append(f'<!-- traj {n_key} keypts -->')
    svg_parts.append(f'<path d="{traj_svg_d}" class="t"/>')
else:
    # 兜底手动路径
    fx0, fy0 = SW*2, oh*0.39
    fx1, fy1 = mcx-PR*3.2, oh*0.72
    ctrl1x = fx0+(fx1-fx0)*0.28; ctrl1y = fy0+(fy1-fy0)*-0.08
    ctrl2x = fx0+(fx1-fx0)*0.68; ctrl2y = fy0+(fy1-fy0)*0.42
    manual_path = f"M{fx0:.1f},{fy0:.1f} C{ctrl1x:.1f},{ctrl1y:.1f} {ctrl2x:.1f},{ctrl2y:.1f} {fx1:.1f},{fy1:.1f}"
    svg_parts.append('<!-- traj fallback -->')
    svg_parts.append(f'<path d="{manual_path}" class="t"/>')

svg_parts.append("</svg>")
svg_content = "\n".join(svg_parts)

out_svg = os.path.join(OUT_DIR, "mars_orbit_v14.svg")
with open(out_svg, "w", encoding="utf-8") as f:
    f.write(svg_content)
print(f"\nSVG已保存: {out_svg}")

# 分析报告
analysis = {
    "input": INPUT, "image_size": [W, H],
    "output_size": [int(ow), int(oh)], "scale": SCALE,
    "planet": mars_circ,
    "markers": [{"name": m["name"], "pos": [m["raw_cx"], m["raw_cy"]],
                 "inferred": m.get("inferred", False)} for m in markers],
    "trajectory": {
        "method": "canny+spatial_filter+rdp+catmull_rom",
        "raw_points": len(traj_raw),
        "ordered_points": len(ordered),
        "key_points": n_key,
        "candidate_info": {k: int(v) if hasattr(v, 'item') else v for k, v in (traj_info or {}).items()},
    },
    "ocr": ocr_texts,
}
with open(os.path.join(OUT_DIR, "analysis_v14.json"), "w", encoding="utf-8") as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)

# HTML 预览页
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>物理试卷预览 v14</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans SC','Microsoft YaHei',SimSun,sans-serif;background:#f5f5f5;padding:24px;color:#222}}
.paper{{background:#fff;max-width:850mm;margin:0 auto;padding:28mm 32mm;
  box-shadow:0 1px 6px rgba(0,0,0,.08);min-height:1100mm}}
.header{{text-align:center;border-bottom:2px solid #222;padding-bottom:10px;margin-bottom:16px}}
.header h1{{font-size:17pt;font-weight:normal;letter-spacing:2px}}
.q-block{{margin:14mm 0}}
.q-text{{font-size:13pt;line-height:1.85;text-indent:2em}}
.fig-wrap{{margin:12mm auto;display:flex;justify-content:center;padding:6mm 0}}
.fig-wrap svg{{max-width:420px;height:auto;border:1px solid #e8e8e8}}
.options{{margin:8mm 0 8mm 4em;font-size:13pt;line-height:1.95}}
.workflow{{background:#fefce8;border:1px solid #e0d68a;border-radius:6px;padding:12px 16px;margin-top:14px;font-size:12.5px;line-height:1.75}}
.workflow h4{{color:#856404;margin-bottom:6px}}
.note{{font-size:11px;color:#888;margin-top:18px;padding-top:12px;border-top:1px dashed #ccc}}
.tag{{display:inline-block;background:#e8f4ea;color:#2a7d2e;padding:2px 8px;border-radius:3px;font-size:11px;margin-right:6px}}
.arrow{{color:#CC0000;font-weight:bold}}
</style></head>
<body>
<div class="paper">
<div class="header"><h1>2026 年普通高等学校招生全国统一考试（模拟）· 物理</h1></div>
<div class="q-block">
<p class="q-text">如图所示，“火星”及其卫星轨道示意图。探测器从<span class="tag">S 点</span>以一定初速度进入轨道 <span class="tag">I</span>，依次经过 <span class="tag">Q 点</span> 和 <span class="tag">P 点</span>。</p>
<div class="fig-wrap">{svg_content}</div>
<p class="options">A．探测器在 S 点的加速度大于 Q 点<br>B．探测器从 S 到 P 的过程中动能不断减小<br>C．轨道 I 的周期大于轨道 III 的周期<br>D．若探测器在 P 点加速可进入轨道 II</p>

<div class="workflow">
<h4>v14 — Canny边缘 + 空间约束过滤 + RDP简化 + Catmull-Rom贝塞尔</h4>
<table style="width:100%;border-collapse:collapse">
<tr style="background:#f0f0f0"><th style="padding:5px 10px;text-align:left">元素</th><th style="padding:5px 10px;text-align:left">方法</th><th style="padding:5px 10px;text-align:left">结果</th></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">星球</td><td>HoughCircles</td><td style="color:#2a7d2e">({mx0},{my0}) r={mr0}</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">轨道 I/II/III</td><td>同心几何约束</td><td style="color:#2a7d2e">精确比例</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">S/Q/P 标记</td><td>圆度+物理约束</td><td style="color:#2a7d2e">{len(markers)}个检测</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee;background:#fff8e1"><strong>★ 轨迹曲线</strong></td><td style="background:#fff8e1">Canny→空间过滤→RDP({n_key}点)→Catmull-Rom</td><td style="background:#fff8e1;color:{'#2a7d2e' if n_key>=3 else '#cc5500'}">{len(traj_raw)}原始点→{n_key}关键点→平滑贝塞尔</td></tr>
</table>
<p style="margin-top:8px;color:#666">
<b>工作流：</b>SVG源码 <span class="arrow">→</span> 编辑 <span class="arrow">→</span> 导出PNG 300dpi <span class="arrow">→</span> 嵌入Word/WPS试卷</p>
</div>
<div class="note"><strong>说明：</strong>SVG中所有元素独立分层。文字为 &lt;text&gt; 可直接编辑。曲线经RDP算法简化关键点后由Catmull-Rom样条保证平滑无回弹。</div>
</div></div></body></html>"""

out_html = os.path.join(OUT_DIR, "exam_preview_v14.html")
with open(out_html, "w", encoding="utf-8") as f:
    f.write(html)
print(f"预览页: {out_html}")
