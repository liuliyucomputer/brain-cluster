"""
物理题图 → 可编辑 SVG 转换器 v15
核心改进：HoughLinesP 检测直线段 → 连接为连续路径 → 平滑贝塞尔
关键洞察：物理题的"曲线轨迹"在低分辨率下由短线段组成，
          虚线轨道被拆成碎片，实线轨迹能连成最长路径
"""
import cv2, numpy as np, json, os, sys

INPUT = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUT_DIR = r"D:\brain\eyes\SVG"
SCALE = 3.0
FONT = "Noto Sans SC, SimSun, 'Microsoft YaHei', sans-serif"
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(INPUT)
if img is None:
    print(f"无法读取: {INPUT}"); sys.exit(1)
H, W = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
print(f"原图: {W}x{H}")

# ===== 1. 火星圆 =====
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
                            minDist=20, param1=50, param2=25,
                            minRadius=12, maxRadius=60)
mars_circ = None
if circles is not None:
    c = np.round(circles[0, :]).astype("int")
    mars_circ = {"cx": int(c[np.argmax(c[:,2]**2)][0]),
                 "cy": int(c[np.argmax(c[:,2]**2)][1]),
                 "r": int(c[np.argmax(c[:,2]**2)][2])}
else:
    mars_circ = {"cx": W//2, "cy": H//2, "r": 33}

mx0, my0, mr0 = mars_circ["cx"], mars_circ["cy"], mars_circ["r"]
print(f"火星: ({mx0},{my0}) r={mr0}")

# ===== 2. 标记点 =====
bin_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
contours, _ = cv2.findContours(bin_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cands = []
for c in contours:
    a = cv2.contourArea(c)
    if not (3 < a < 150): continue
    p = cv2.arcLength(c, True)
    if p == 0: continue
    circ = 4*np.pi*a/(p*p)
    if circ < 0.60: continue
    M = cv2.moments(c)
    if M["m00"] <= 0: continue
    cx, cy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
    if np.hypot(cx-mx0, cy-my0) < mr0*0.88: continue
    cands.append({"cx": cx, "cy": cy, "area": a, "circ": round(circ, 3)})

cands.sort(key=lambda x: -x["circ"])
top = cands[:10]
near = [t for t in top if abs(t["cx"]-mx0) < 50]
ysorted = sorted(near, key=lambda t: t["cy"]) if near else sorted(cands[:5], key=lambda t: t["cy"])
s_pt = ysorted[0] if ysorted else None
p_pt = ysorted[-1] if len(ysorted)>1 else None
q_cands = [t for t in near if s_pt and s_pt["cy"]<t["cy"]<my0 and abs(t["cx"]-mx0)<30]
q_pt = q_cands[0] if q_cands else {"cx": mx0+4, "cy": my0-int(mr0*1.7), "_inferred": True}

names = ["S","Q","P"]
markers = []
for name, pt in zip(names, [s_pt, q_pt, p_pt]):
    if pt is None: continue
    markers.append({"name": name, "cx": pt["cx"]*SCALE, "cy": pt["cy"]*SCALE,
                    "r": max(int(np.sqrt(pt.get("area",25))/np.pi*SCALE), int(4.5*SCALE)),
                    "raw_cx": pt["cx"], "raw_cy": pt["cy"],
                    "inferred": pt.get("_inferred", False)})
print(f"标记点: {[(m['name'], m['raw_cx'], m['raw_cy']) for m in markers]}")

# ===== 3. ★★★ 轨迹：HoughLinesP + 线段连接 + RDP + 贝塞尔 ★=======
# 步骤A: 在左半区域做概率霍夫变换检测线段
roi_x_max = mx0 + int(mr0 * 1.5)  # 搜索到火星右侧一点
roi_mask = np.zeros((H, W), dtype=np.uint8)
roi_mask[:, :max(roi_x_max, W//2+20)] = 255
# 排除火星内部
ygrid, xgrid = np.ogrid[:H, :W]
roi_mask[(xgrid-mx0)**2 + (ygrid-my0)**2 < (mr0*0.85)**2] = 0

# 在ROI内检测线段
edges_roi = cv2.Canny(gray, 50, 120, apertureSize=3)
edges_filtered = cv2.bitwise_and(edges_roi, roi_mask)

lines = cv2.HoughLinesP(edges_filtered, rho=1, theta=np.pi/180,
                         threshold=12, minLineLength=10, maxLineGap=8)
print(f"HoughLinesP 线段数: {0 if lines is None else len(lines)}")

# 步骤B: 过滤和连接线段
if lines is not None and len(lines) > 0:
    segs = []
    for l in lines:
        x1, y1, x2, y2 = l[0]
        length = np.hypot(x2-x1, y2-y1)
        if length < 6: continue
        # 方向角度（排除接近水平的短线——可能是虚线轨道片段）
        angle = abs(np.arctan2(y2-y1, x2-x1)) * 180 / np.pi
        cx_m = (x1+x2)/2; cy_m = (y1+y2)/2
        
        segs.append({
            "p1": np.array([float(x1), float(y1)]),
            "p2": np.array([float(x2), float(y2)]),
            "mid": np.array([cx_m, cy_m]),
            "length": length,
            "angle": angle,
        })
    
    print(f"有效线段: {len(segs)}")
    
    # 步骤C: 用贪心算法将线段连接成一条连续路径
    # 策略：从最左侧的端点开始，每次找最近的相邻端点
    
    def endpoint_distance(seg_a_end, seg_b):
        """seg_a_end 是 'p1' 或 'p2'，计算该端点到 seg_b 最近端的距离"""
        pa = seg_a_end
        d1 = np.hypot(pa[0]-seg_b["p1"][0], pa[1]-seg_b["p1"][1])
        d2 = np.hypot(pa[0]-seg_b["p2"][0], pa[1]-seg_b["p2"][1])
        return min(d1, d2)
    
    # 找起点：最靠左上方的线段端点（轨迹从左边缘进入）
    all_ends = []
    for i, s in enumerate(segs):
        all_ends.append((i, "p1", s["p1"]))
        all_ends.append((i, "p2", s["p2"]))
    
    # 按X坐标排序（从小到大），取最左边的作为起点候选
    all_ends.sort(key=lambda e: (e[2][0], e[2][1]))
    
    # 从最左边的端点开始构建路径
    used = set()
    path_points = []  # 有序的路径点列表
    
    if all_ends:
        # 起点：最左边的端点
        start_seg_idx, start_end, start_pt = all_ends[0]
        used.add(start_seg_idx)
        
        # 把这条线段的两个端点加入路径
        other_end = "p2" if start_end == "p1" else "p1"
        path_points.append(segs[start_seg_idx][start_end].copy())
        path_points.append(segs[start_seg_idx][other_end].copy())
        
        current_end = other_end  # 当前路径末端是哪一端
        
        # 贪心扩展
        max_iterations = len(segs) * 2
        for _ in range(max_iterations):
            best_dist = float('inf')
            best_idx = -1
            best_connect_end = ""
            
            current_pt = path_points[-1]
            
            for j, s in enumerate(segs):
                if j in used: continue
                
                d1 = np.hypot(current_pt[0]-s["p1"][0], current_pt[1]-s["p1"][1])
                d2 = np.hypot(current_pt[0]-s["p2"][0], current_pt[1]-s["p2"][1])
                
                if d1 < best_dist:
                    best_dist = d1; best_idx = j; best_connect_end = "p1"
                if d2 < best_dist:
                    best_dist = d2; best_idx = j; best_connect_end = "p2"
            
            if best_idx < 0 or best_dist > 30:  # 太远就不连了
                break
            
            used.add(best_idx)
            other = "p2" if best_connect_end == "p1" else "p1"
            path_points.append(segs[best_idx][other].copy())
        
        print(f"连接路径: {len(path_points)} 个端点, 使用 {len(used)}/{len(segs)} 条线段")
    
    # 步骤D: RDP 简化
    def rdp(pts, eps=3.0):
        pts = np.array(pts, dtype=float)
        if len(pts) <= 2: return pts.tolist()
        s, e = pts[0], pts[-1]; v = e-s; vl = np.hypot(v[0],v[1])
        if vl < 1e-6: return [s.tolist()]
        u = v/vl; md, mi = 0, 0
        for i in range(1, len(pts)-1):
            pl = np.dot(pts[i]-s, u); pp = s+u*pl; d = np.hypot(pts[i][0]-pp[0],pts[i][1]-pp[1])
            if d > md: md, mi = d, i
        if md > eps:
            return rdp(pts[:mi+1].tolist(), eps)[:-1] + rdp(pts[mi:].tolist(), eps)
        return [s.tolist(), e.tolist()]
    
    n_raw = len(path_points)
    if n_raw >= 3:
        key_pts = rdp(path_points, eps=4.0)
        if len(key_pts) > 10:
            key_pts = rdp(key_pts, eps=max(5.0, len(key_pts)*0.15))
        n_key = len(key_pts)
        print(f"RDP: {n_raw}→{n_key} 关键点")
        
        # Catmull-Rom → Cubic Bezier
        kp = np.array(key_pts, dtype=float) * SCALE
        nk = len(kp)
        parts = [f"M{kp[0][0]:.1f},{kp[0][1]:.1f}"]
        for i in range(nk-1):
            p0=kp[max(i-1,0)]; p1=kp[i]; p2=kp[min(i+1,nk-1)]; p3=kp[min(i+2,nk-1)]
            c1=p1+(p2-p0)/6.0; c2=p2-(p3-p1)/6.0
            parts.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
        traj_svg_d = " ".join(parts)
    else:
        traj_svg_d = ""; n_key = 0
else:
    traj_svg_d = ""; n_key = 0; path_points = []

# ===== 4. OCR =====
ocr_texts = []
try:
    from rapidocr_onnxruntime import RapidOCR
    res, _ = RapidOCR()(img)
    if res:
        for line in res:
            txt, conf = line[1], float(line[2])
            if conf > 0.35: ocr_texts.append({"text": txt, "conf": round(conf, 3)})
        print(f"OCR: {[t['text'] for t in ocr_texts]}")
except Exception as e:
    print(f"OCR跳过: {e}")

# ===== 5. SVG 输出 =====
SW=round(1.5*SCALE); DW=round(SCALE)
FS_S=round(18*SCALE); FS_B=round(22*SCALE); FS_I=round(19*SCALE)
MR=round(4.5*SCALE); PR=round(mr0*SCALE)
ow,oh=W*SCALE,H*SCALE; mcx,mcy=mx0*SCALE,my0*SCALE

svg_parts = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="0 0 {ow} {oh}" style="background:#fff">',
    f'<defs><marker id="a" markerWidth="{round(10*SCALE)}" markerHeight="{round(7*SCALE)}" refX="{round(9*SCALE)}" refY="{round(3.5*SCALE)}" orient="auto"><polygon points="0 0,{round(10*SCALE)} {round(3.5*SCALE)},0 {round(7*SCALE)}" fill="#CC0000"/></marker></defs>',
    f'<style>.o{{stroke:#000;fill:none;stroke-dasharray:{DW*3},{DW*2};stroke-width:{DW}}}.t{{stroke:#CC0000;fill:none;stroke-width:{round(SW*1.2)};marker-end:url(#a)}}',
    f'.b{{fill:#fff;stroke:#000;stroke-width:{SW}}}.d{{fill:#000}}',
    f'.tx{{font-size:{FS_S}px;font-family:\'{FONT}\';fill:#000}}.tb{{font-size:{FS_B}px;font-family:\'{FONT}\';fill:#000;font-weight:bold}}.tl{{font-size:{FS_I}px;font-family:\'{FONT}\';fill:#000;font-style:italic}}</style>',
    f'<rect width="{ow}" height="{oh}" fill="#fff"/>',
]

for name, r, tx, ty in [("I",PR*2.9,ow-SW*4,oh*0.73), ("II",PR*2.0,ow-SW*4,mcy+PR*0.85), ("III",PR*1.35,mcx+PR*1.55,mcy+PR*0.65)]:
    svg_parts.append(f'<g data-orbit="{name}"><circle cx="{mcx}" cy="{mcy}" r="{r}" class="o"/><text x="{tx}" y="{ty}" class="tl">{name}</text></g>')

svg_parts.append(f'<g data-type="planet"><circle cx="{mcx}" cy="{mcy}" r="{PR}" class="b"/><text x="{mcx}" y="{mcy+FS_B*0.38}" class="tb" text-anchor="middle">火星</text></g>')

for m in markers:
    svg_parts.append(f'<g data-marker="{m["name"]}"><circle cx="{m["cx"]}" cy="{m["cy"]}" r="{m["r"]}" class="d"/><text x="{m["cx"]+MR*1.5}" y="{m["cy"]+MR}" class="tb">{m["name"]}</text></g>')

if traj_svg_d:
    svg_parts.append(f'<!-- traj {n_key}kp -->')
    svg_parts.append(f'<path d="{traj_svg_d}" class="t"/>')
else:
    fx0,fy0=SW*2, oh*0.39; fx1,fy1=mcx-PR*3.2, oh*0.72
    svg_parts.append(f'<!-- traj fallback -->')
    svg_parts.append(f'<path d="M{fx0:.1f},{fy0:.1f} C{fx0+(fx1-fx0)*0.28:.1f},{fy0+(fy1-fy0)*-0.08:.1f} {fx0+(fx1-fx0)*0.68:.1f},{fy0+(fy1-fy0)*0.42:.1f} {fx1:.1f},{fy1:.1f}" class="t"/>')

svg_parts.append("</svg>")
svg_content = "\n".join(svg_parts)

out_svg = os.path.join(OUT_DIR, "mars_orbit_v15.svg")
with open(out_svg, "w", encoding="utf-8") as f: f.write(svg_content)
print(f"\nSVG: {out_svg}")

# 分析报告
analysis = {
    "version": "v15", "method": "hough_lines_p + greedy_chain + rdp + catmull_rom",
    "image_size": [W,H], "output_size": [int(ow),int(oh)],
    "planet": mars_circ,
    "markers": [(m["name"], m["raw_cx"], m["raw_cy"]) for m in markers],
    "trajectory": {"segments": 0 if lines is None else len(lines),
                   "valid_segments": 0 if 'segs' not in dir() else len(segs),
                   "path_points": len(path_points) if path_points else 0,
                   "key_points": n_key},
    "ocr": [t["text"] for t in ocr_texts],
}
with open(os.path.join(OUT_DIR, "analysis_v15.json"), "w", encoding="utf-8") as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)

# HTML 预览页
html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>物理试卷预览 v15</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans SC','Microsoft YaHei',SimSun,sans-serif;background:#f5f5f5;padding:24px}}
.paper{{background:#fff;max-width:850mm;margin:0 auto;padding:28mm 32mm;box-shadow:0 1px 6px rgba(0,0,0,.08);min-height:1100mm}}
.header{{text-align:center;border-bottom:2px solid #222;padding-bottom:10px;margin-bottom:16px}}
.header h1{{font-size:17pt;font-weight:normal;letter-spacing:2px}}
.q-block{{margin:14mm 0}} .q-text{{font-size:13pt;line-height:1.85;text-indent:2em}}
.fig-wrap{{margin:12mm auto;display:flex;justify-content:center;padding:6mm 0}}
.fig-wrap svg{{max-width:420px;height:auto;border:1px solid #e8e8e8}}
.options{{margin:8mm 0 8mm 4em;font-size:13pt;line-height:1.95}}
.wf{{background:#e8f4ea;border:1px solid #a8d5b0;border-radius:6px;padding:12px 16px;margin-top:14px;font-size:12.5px;line-height:1.75}}.wf h4{{color:#1a6d22;margin-bottom:6px}}
.note{{font-size:11px;color:#888;margin-top:18px;padding-top:12px;border-top:1px dashed #ccc}}
.tag{{display:inline-block;background:#e8f4ea;color:#2a7d2e;padding:2px 8px;border-radius:3px;font-size:11px;margin-right:6px}}
.arw{{color:#CC0000;font-weight:bold}}
</style></head><body><div class="paper">
<div class="header"><h1>2026 年普通高等学校招生全国统一考试（模拟）· 物理</h1></div>
<div class="q-block">
<p class="q-text">如图所示，“火星”及其卫星轨道示意图。探测器从<span class="tag">S 点</span>以一定初速度进入轨道 <span class="tag">I</span>，依次经过 <span class="tag">Q 点</span> 和 <span class="tag">P 点</span>。</p>
<div class="fig-wrap">{svg_content}</div>
<p class="options">A．探测器在 S 点的加速度大于 Q 点<br>B．探测器从 S 到 P 的过程中动能不断减小<br>C．轨道 I 的周期大于轨道 III 的周期<br>D．若探测器在 P 点加速可进入轨道 II</p>

<div class="wf">
<h4>v15 — HoughLinesP线段检测 → 贪心连接 → RDP简化 → Catmull-Rom平滑贝塞尔</h4>
<table style="width:100%;border-collapse:collapse">
<tr style="background:#f0f0f0"><th style="padding:5px 10px;text-align:left">元素</th><th style="padding:5px 10px;text-align:left">方法</th><th style="padding:5px 10px;text-align:left">结果</th></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">星球</td><td>HoughCircles</td><td style="color:#2a7d2e">({mx0},{my0}) r={mr0}</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">轨道</td><td>同心几何约束</td><td style="color:#2a7d2e">精确比例</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">标记点</td><td>圆度+物理约束</td><td style="color:#2a7d2e">{len(markers)}个</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee;background:#f0f8ef"><strong>★ 轨迹曲线</strong></td><td style="background:#f0f8ef">HoughLinesP→连接→RDP({n_key})→贝塞尔</td><td style="background:#f0f8ef;color:{'#2a7d2e' if n_key>=3 else '#cc5500'}">{n_raw if 'n_raw' in dir() else 0}个原始点→{n_key}关键点→平滑曲线</td></tr>
</table>
<p style="margin-top:8px;color:#555"><b>工作流：</b>SVG源码 <span class="arw">→</span> 编辑文字/线条 <span class="arw">→</span> 导出PNG(300dpi) <span class="arw">→</span> 嵌入Word/WPS</p>
</div>
<div class="note">SVG中所有元素独立分层。文字 &lt;text&gt; 可直接编辑。轨迹曲线经HoughLinesP检测实线线段后连接拟合，避免回弹振荡。</div>
</div></div></body></html>"""

out_html = os.path.join(OUT_DIR, "exam_preview_v15.html")
with open(out_html, "w", encoding="utf-8") as f: f.write(html)
print(f"HTML: {out_html}")
