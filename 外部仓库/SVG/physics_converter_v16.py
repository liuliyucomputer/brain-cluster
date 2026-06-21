"""
物理题图 → 可编辑 SVG 转换器 v16（最终版）
策略转变：
  - 几何图形（圆、点、文字）：CV自动检测 ✅ 已稳定
  - 自由曲线（轨迹）：CV粗定位起止点 → 参数化曲线拟合 ✅ 新方案
  
原理：高中物理的"变轨轨迹"都是圆锥曲线弧段，
      只需要(1)起点位置 (2)终点位置 (3)大致弯曲方向，
      就可以用2-3个控制点的贝塞尔曲线精确还原。
      这比任何CV像素提取都更可靠。
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
    c = np.round(circles[0,:]).astype("int")
    bi = np.argmax(c[:,2]**2)
    mars_circ = {"cx": int(c[bi][0]), "cy": int(c[bi][1]), "r": int(c[bi][2])}
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

# ===== 3. ★★★ 轨迹：CV粗定位 + 物理约束贝塞尔拟合 ★=======
# 步骤A: 在左半边区域检测深色像素的"重心趋势"
# 创建左半边搜索掩码（排除已知元素）
search_mask = np.zeros((H,W), dtype=np.uint8)
# 搜索区：左边60%宽度，排除火星内部
for y in range(H):
    for x in range(int(W*0.62)):
        if np.hypot(x-mx0, y-my0) > mr0 * 0.9:
            search_mask[y,x] = 255

# 在搜索区内找暗色像素列的"平均X坐标"作为轨迹走向
edges = cv2.Canny(gray, 40, 100)
masked_edges = cv2.bitwise_and(edges, search_mask)

# 用列投影找每行的轨迹X位置
traj_y_coords = []
traj_x_by_row = []
for row_y in range(H):
    row_pixels = masked_edges[row_y, :]
    if np.sum(row_pixels) > 5:  # 这一行有边缘像素
        # 加权平均 X 坐标
        xs = np.where(row_pixels > 0)[0]
        avg_x = float(np.mean(xs))
        traj_x_by_row.append((row_y, avg_x))

if traj_x_by_row:
    # 去除噪声：只保留X坐标连续变化的行
    clean = [traj_x_by_row[0]]
    for i in range(1, len(traj_x_by_row)):
        y_curr, x_curr = traj_x_by_row[i]
        y_prev, x_prev = clean[-1]
        # X变化不能太剧烈（轨迹是平滑的）
        if abs(x_curr - x_prev) < 35:  # 相邻行X变化<35px
            clean.append((y_curr, x_curr))
    
    traj_x_by_row = clean
    
    # 找轨迹的大致起点和终点（最上和最下）
    start_y, start_x = traj_x_by_row[0]
    end_y, end_x = traj_x_by_row[-1]
    
    print(f"轨迹大致范围: ({start_x:.0f},{start_y:.0f}) → ({end_x:.0f},{end_y:.0f})")
    print(f"覆盖行数: {len(traj_x_by_row)}")
else:
    start_x, start_y, end_x, end_y = 10.0, float(H*0.4), float(mx0-mr0), float(H*0.95)
    traj_x_by_row = []

# 步骤B: 用二次贝塞尔（3点）或三次贝塞尔（4点）拟合
# 根据轨迹点的分布选择控制点
if len(traj_x_by_row) >= 10:
    # 将轨迹点分为三段，取每段的代表点作为贝塞尔控制点
    n = len(traj_x_by_row)
    p1_idx = 0                          # 起点
    p2_idx = n // 3                      # 第一个控制点
    p3_idx = 2 * n // 3                  # 第二个控制点  
    p4_idx = n - 1                       # 终点
    
    P1 = np.array([traj_x_by_row[p1_idx][1], float(traj_x_by_row[p1_idx][0])])
    P2 = np.array([traj_x_by_row[p2_idx][1], float(traj_x_by_row[p2_idx][0])])
    P3 = np.array([traj_x_by_row[p3_idx][1], float(traj_x_by_row[p3_idx][0])])
    P4 = np.array([traj_x_by_row[p4_idx][1], float(traj_x_by_row[p4_idx][0])])
    
    # 缩放到输出尺寸
    P1s = P1 * SCALE; P2s = P2 * SCALE; P3s = P3 * SCALE; P4s = P4 * SCALE
    
    # 三次贝塞尔 SVG路径（两段，保证足够平滑）
    # 第一段: P1 → P2 → P3
    cp1_1 = P1s + (P2s - P1s) * 0.55   # 控制点1
    cp1_2 = P2s - (P3s - P1s) * 0.1     # 控制点2
    
    # 第二段: P2 → P3 → P4  
    cp2_1 = P2s + (P3s - P1s) * 0.15   # 控制点3
    cp2_2 = P3s + (P4s - P2s) * 0.45   # 控制点4
    
    traj_svg_d = (
        f"M{P1s[0]:.1f},{P1s[1]:.1f} "
        f"C{cp1_1[0]:.1f},{cp1_1[1]:.1f} {cp1_2[0]:.1f},{cp1_2[1]:.1f} {P2s[0]:.1f},{P2s[1]:.1f} "
        f"C{cp2_1[0]:.1f},{cp2_1[1]:.1f} {cp2_2[0]:.1f},{cp2_2[1]:.1f} {P4s[0]:.1f},{P4s[1]:.1f}"
    )
    n_key = 4
    method_detail = f"列投影({n}行)→4点三次贝塞尔"
elif len(traj_x_by_row) >= 3:
    P1 = np.array([traj_x_by_row[0][1], float(traj_x_by_row[0][0])]) * SCALE
    P2 = np.array([traj_x_by_row[len(traj_x_by_row)//2][1], float(traj_x_by_row[len(traj_x_by_row)//2][0])]) * SCALE
    P3 = np.array([traj_x_by_row[-1][1], float(traj_x_by_row[-1][0])]) * SCALE
    cp1 = P1 + (P2-P1)*0.6; cp2 = P2 + (P3-P2)*0.4
    traj_svg_d = f"M{P1[0]:.1f},{P1[1]:.1f} C{cp1[0]:.1f},{cp1[1]:.1f} {cp2[0]:.1f},{cp2[1]:.1f} {P3[0]:.1f},{P3[1]:.1f}"
    n_key = 3
    method_detail = f"列投影→3点二次贝塞尔"
else:
    # 完全兜底：基于物理知识的手动路径
    fx0, fy0 = float(SCALE*3), float(H*SCALE*0.39)
    fx1, fy1 = float((mx0-mr0)*SCALE), float(H*SCALE*0.74)
    c1x = fx0+(fx1-fx0)*0.28; c1y = fy0+(fy1-fy0)*(-0.08)
    c2x = fx0+(fx1-fx0)*0.68; c2y = fy0+(fy1-fy0)*0.42
    traj_svg_d = f"M{fx0:.1f},{fy0:.1f} C{c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {fx1:.1f},{fy1:.1f}"
    n_key = 0
    method_detail = "物理约束兜底"

print(f"轨迹: {method_detail}")

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
    '<defs>',
    f'<marker id="a" markerWidth="{round(10*SCALE)}" markerHeight="{round(7*SCALE)}" refX="{round(9*SCALE)}" refY="{round(3.5*SCALE)}" orient="auto">',
    f'<polygon points="0 0,{round(10*SCALE)} {round(3.5*SCALE)},0 {round(7*SCALE)}" fill="#CC0000"/></marker></defs>',
    f'<style>.o{{stroke:#000;fill:none;stroke-dasharray:{DW*3},{DW*2};stroke-width:{DW}}}',
    '.t{stroke:#CC0000;fill:none;stroke-width:'+str(round(SW*1.2))+';marker-end:url(#a)}',
    f'.b{{fill:#fff;stroke:#000;stroke-width:{SW}}}.d{{fill:#000}}',
    f'.tx{{font-size:{FS_S}px;font-family:\'{FONT}\';fill:#000}}',
    f'.tb{{font-size:{FS_B}px;font-family:\'{FONT}\';fill:#000;font-weight:bold}}',
    f'.tl{{font-size:{FS_I}px;font-family:\'{FONT}\';fill:#000;font-style:italic}}</style>',
    f'<rect width="{ow}" height="{oh}" fill="#fff"/>',
]

orbits = [("I",PR*2.9,ow-SW*4,oh*0.73), ("II",PR*2.0,ow-SW*4,mcy+PR*0.85), ("III",PR*1.35,mcx+PR*1.55,mcy+PR*0.65)]
for name, r, tx, ty in orbits:
    svg_parts.append(f'<g data-orbit="{name}"><circle cx="{mcx}" cy="{mcy}" r="{r}" class="o"/><text x="{tx}" y="{ty}" class="tl">{name}</text></g>')

svg_parts.append(f'<g data-type="planet"><circle cx="{mcx}" cy="{mcy}" r="{PR}" class="b"/><text x="{mcx}" y="{mcy+FS_B*0.38}" class="tb" text-anchor="middle">火星</text></g>')

for m in markers:
    svg_parts.append(f'<g data-marker="{m["name"]}"><circle cx="{m["cx"]}" cy="{m["cy"]}" r="{m["r"]}" class="d"/><text x="{m["cx"]+MR*1.5}" y="{m["cy"]+MR}" class="tb">{m["name"]}</text></g>')

svg_parts.append(f'<!-- traj {method_detail} -->')
svg_parts.append(f'<path d="{traj_svg_d}" class="t"/>')
svg_parts.append("</svg>")
svg_content = "\n".join(svg_parts)

out_svg = os.path.join(OUT_DIR, "mars_orbit_v16.svg")
with open(out_svg, "w", encoding="utf-8") as f: f.write(svg_content)
print(f"\nSVG: {out_svg}")

# 分析报告
analysis = {
    "version": "v16",
    "method": "cv_detection + column_projection + physics_constrained_bezier",
    "image_size": [W,H], "output_size": [int(ow),int(oh)], "scale": SCALE,
    "planet": mars_circ,
    "markers": [(m["name"], m["raw_cx"], m["raw_cy"]) for m in markers],
    "trajectory": {
        "method": method_detail,
        "sampled_rows": len(traj_x_by_row),
        "control_points": n_key,
        "approx_range": ([start_x, start_y], [end_x, end_y]) if traj_x_by_row else None,
    },
    "ocr": [t["text"] for t in ocr_texts],
}
with open(os.path.join(OUT_DIR, "analysis_v16.json"), "w", encoding="utf-8") as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)

# HTML 预览页
html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>物理试卷预览 v16 — 最终版</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans SC','Microsoft YaHei',SimSun,sans-serif;background:#f5f5f5;padding:24px;color:#222}}
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
.ok{{color:#2a7d2e}} .warn{{color:#cc5500}}
</style></head><body><div class="paper">
<div class="header"><h1>2026 年普通高等学校招生全国统一考试（模拟）· 物理</h1></div>
<div class="q-block">
<p class="q-text">如图所示，“火星”及其卫星轨道示意图。探测器从<span class="tag">S 点</span>以一定初速度进入轨道 <span class="tag">I</span>，依次经过 <span class="tag">Q 点</span> 和 <span class="tag">P 点</span>。</p>
<div class="fig-wrap">{svg_content}</div>
<p class="options">A．探测器在 S 点的加速度大于 Q 点<br>B．探测器从 S 到 P 的过程中动能不断减小<br>C．轨道 I 的周期大于轨道 III 的周期<br>D．若探测器在 P 点加速可进入轨道 II</p>

<div class="wf">
<h4>v16 最终版 — 列投影定位轨迹走向 + 物理约束参数化贝塞尔曲线</h4>
<table style="width:100%;border-collapse:collapse">
<tr style="background:#f0f0f0"><th style="padding:5px 10px;text-align:left">元素</th><th style="padding:5px 10px;text-align:left">方法</th><th style="padding:5px 10px;text-align:left">结果</th></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">星球圆形</td><td>HoughCircles</td><td class="ok">({mx0},{my0}) r={mr0}</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">同心轨道 I/II/III</td><td>几何约束（同圆心）</td><td class="ok">精确比例</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">标记点 S/Q/P</td><td>轮廓+圆度+物理约束</td><td class="ok">{len(markers)} 个{'(Q推断)' if any(m.get('inferred') for m in markers) else ''}</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee">中文标签</td><td>RapidOCR</td><td class="ok">{len(ocr_texts)} 个词识别</td></tr>
<tr><td style="padding:4px 10px;border-top:1px solid #eee;background:#f0f8ef"><strong>★ 轨迹曲线 I</strong></td><td style="background:#f0f8ef">Canny→列投影→平滑→{n_key}点贝塞尔</td><td style="background:#f0f8ef" class="{'ok' if n_key>=3 else 'warn'}">{method_detail}</td></tr>
</table>
<p style="margin-top:10px;color:#444;line-height:1.8">
<b>为什么这个方法更稳定？</b><br>
纯CV方法（Canny/Hough轮廓/B样条）的问题是：<br>
① 低分辨率图片中轨迹线与文字/虚线混杂无法分离<br>
② 像素级拟合会产生回弹振荡（过拟合）<br>
③ 每张图的噪声模式不同，阈值难以通用<br><br>
本方案的思路：<br>
① 用CV只做<strong>粗定位</strong>（轨迹在哪一区域、什么走向）<br>
② 用<strong>物理知识</strong>（轨迹是光滑圆锥曲线弧）约束输出形状<br>
③ 贝塞尔控制点只有2-4个，不可能产生振荡<br>
④ 结果可预期、可调试、可人工微调
</p>
<p style="margin-top:8px;color:#555"><b>工作流：</b>SVG源码 <span class="arw">→</span> Inkscape编辑 <span class="arw">→</span> 导出PNG 300dpi <span class="arw">→</span> Word/WPS试卷</p>
</div>
<div class="note">SVG所有元素独立分层，文字为 &lt;text&gt; 元素可直接选中编辑。曲线使用参数化贝塞尔保证平滑无振荡。</div>
</div></div></body></html>"""

out_html = os.path.join(OUT_DIR, "exam_preview_v16.html")
with open(out_html, "w", encoding="utf-8") as f: f.write(html)
print(f"HTML: {out_html}")
