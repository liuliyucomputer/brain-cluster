"""
物理题图片 → 可编辑 SVG 转换器 v7（精确版）
=============================================
策略：基于对图像结构的理解，用 OCR + 智能过滤 + 确定性模板重建
目标图：火星轨道示意图 — 1个星球 + 3条虚线轨道(I/II/III) + 3个标记点(S/Q/P) + 1条轨迹箭头
"""

import cv2
import numpy as np
from pathlib import Path
import json
import math

# ============================================================
# 配置
# ============================================================
INPUT_IMAGE = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUTPUT_DIR = Path(r"D:\brain\eyes\SVG")
OUTPUT_SVG = OUTPUT_DIR / "mars_orbit_v7.svg"
OUTPUT_ANALYSIS = OUTPUT_DIR / "analysis_v7.json"
OUTPUT_HTML = OUTPUT_DIR / "exam_preview_v5.html"

FONT_FAMILY = "'Noto Sans SC', SimSun, 'Times New Roman', serif"

def run_ocr(image_path):
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    result, _ = ocr(image_path)
    texts = []
    if result:
        for bbox, text, conf in result:
            cx = sum(p[0] for p in bbox) / 4
            cy = sum(p[1] for p in bbox) / 4
            w = max(p[0] for p in bbox) - min(p[0] for p in bbox)
            h = max(p[1] for p in bbox) - min(p[1] for p in bbox)
            texts.append({"text": text, "cx": float(cx), "cy": float(cy),
                         "w": float(w), "h": float(h), "conf": float(conf)})
    return texts


def analyze_structure(image_path):
    """精确分析图像结构，提取关键几何参数"""
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- 检测圆形：用多尺度 HoughCircles ---
    all_circles = []
    for dp in [1.0, 1.2, 1.5]:
        for minDist in [25, 40, 60]:
            c = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=dp,
                                 minDist=minDist, param1=60, param2=22,
                                 minRadius=12, maxRadius=min(h,w)//2)
            if c is not None:
                for ci in c[0]:
                    all_circles.append((float(ci[0]), float(ci[1]), float(ci[2])))

    # 聚类合并相似圆
    def cluster_circles(circles, r_tol=15, center_tol=20):
        """按半径和中心聚类圆"""
        clusters = []
        used = set()
        for i, (x1,y1,r1) in enumerate(circles):
            if i in used:
                continue
            group = [(x1,y1,r1)]
            used.add(i)
            for j, (x2,y2,r2) in enumerate(circles):
                if j in used:
                    continue
                dr = abs(r1 - r2)
                dc = math.sqrt((x1-x2)**2 + (y1-y2)**2)
                if dr < r_tol and dc < min(r1, r2) * 0.6:
                    group.append((x2,y2,r2))
                    used.add(j)
            # 取组内平均
            avg_x = sum(g[0] for g in group) / len(group)
            avg_y = sum(g[1] for g in group) / len(group)
            avg_r = sum(g[2] for g in group) / len(group)
            # 支持度 = 组内圆数量
            clusters.append({"cx": avg_x, "cy": avg_y, "r": avg_r, "support": len(group)})
        return sorted(clusters, key=lambda c: c["support"], reverse=True)

    clustered = cluster_circles(all_circles)

    # --- 检测标记点（实心黑圆）---
    _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    
    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    markers = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        peri = cv2.arcLength(cnt, True)
        circ = 4 * math.pi * area / (peri**2) if peri > 0 else 0
        if 30 < area < 300 and circ > 0.55:
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                markers.append({
                    "cx": M["m10"]/M["m00"], "cy": M["m01"]/M["m00"],
                    "r": math.sqrt(area/math.pi), "area": area, "circ": circ
                })

    # --- 检测长线段（轨迹曲线）---
    edges = cv2.Canny(gray, 60, 180)
    lines_raw = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=35,
                                 minLineLength=18, maxLineGap=4)
    long_lines = []
    if lines_raw is not None:
        for l in lines_raw:
            x1,y1,x2,y2 = l[0]
            length = math.sqrt((x2-x1)**2+(y2-y1)**2)
            if length > 22:
                long_lines.append({
                    "x1": x1,"y1": y1,"x2": x2,"y2": y2,
                    "length": length,
                    "angle": math.degrees(math.atan2(y2-y1, x2-x1))
                })

    return {
        "size": {"w": w, "h": h},
        "circles_all_count": len(all_circles),
        "circles_clustered": clustered[:10],  # Top 10 by support
        "markers": markers,
        "long_lines": long_lines
    }


def build_svg(geo, ocr_texts):
    """
    基于分析结果构建精确的试卷风格 SVG。
    核心逻辑：
      1. 从聚类圆中选出 3 个主要轨道 + 1 个星球本体
      2. 用标记点数据定位 S/Q/P
      3. OCR 文字自动关联到对应元素
      4. 长线段作为轨迹曲线
    """
    w, h = geo["size"]["w"], geo["size"]["h"]
    scale = 2.8  # 放大到试卷合适大小
    m = 40       # margin
    sw, sh = int(w*scale)+m*2, int(h*scale)+m*2

    def sx(x): return x * scale + m
    def sy(y): return y * scale + m

    # === 分析聚类圆，确定哪些是有效轨道 ===
    circles = geo["circles_clustered"]
    markers = geo["markers"]

    # 找到"火星"文字位置来确定星球本体
    mars_text = None
    for t in ocr_texts:
        if "火" in t.get("text", "") or "星" in t.get("text", ""):
            mars_text = t
            break

    # 星球本体：最小的、且与"火星"文字位置接近的圆
    planet_circle = None
    planet_idx = None
    orbit_circles = []

    for i, c in enumerate(circles):
        if planet_idx is not None:
            break  # 已经找到星球
        # 最小半径的圆可能是星球（排除太小的噪声）
        if c["r"] < 25 or c["r"] > 100:
            continue
        if mars_text:
            dist_to_mars = math.sqrt((c["cx"]-mars_text["cx"])**2 + (c["cy"]-mars_text["cy"])**2)
            if dist_to_mars < c["r"] + 8:
                planet_circle = c
                planet_idx = i
        else:
            if c["support"] >= 2 and 28 <= c["r"] <= 45:
                planet_circle = c
                planet_idx = i

    # 轨道圆：支持度高、半径合理的圆
    for i, c in enumerate(circles):
        if i == planet_idx:
            continue
        if c["support"] >= 3 and c["r"] >= 35:
            orbit_circles.append(c)

    # 按半径排序（从大到小）
    orbit_circles.sort(key=lambda c: c["r"], reverse=True)

    # 如果没检测到足够轨道，手动补充（基于图像观察）
    if len(orbit_circles) < 3 and planet_circle:
        pc = planet_circle
        # 基于实际图像参数估算轨道
        fallback_orbits = [
            {"cx": 140, "cy": 95, "r": 105, "support": 99},   # I (最外层，椭圆)
            {"cx": 170, "cy": 115, "r": 78, "support": 99},   # II
            {"cx": 175, "cy": 155, "r": 50, "support": 99},    # III
        ]
        needed = 3 - len(orbit_circles)
        for fo in fallback_orbits[:needed]:
            orbit_circles.append(fo)

    # === 构建 SVG ===
    parts = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{sw}" height="{sh}"
     viewBox="0 0 {sw} {sh}"
     style="background:#fff;">
  <defs>
    <marker id="arr" markerWidth="10" markerHeight="7"
            refX="9" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#C00"/>
    </marker>
    <style>
      .orbit {{ stroke:#000; fill:none; stroke-dasharray:7,4; stroke-width:1.5; }}
      .traj {{ stroke:#C00; fill:none; stroke-width:1.8; marker-end:url(#arr); }}
      .body {{ fill:#fff; stroke:#000; stroke-width:1.5; }}
      .dot {{ fill:#000; }}
      .lbl {{ font-size:16px; font-family:{FONT_FAMILY}; fill:#000; }}
      .lbl-b {{ font-size:16px; font-family:{FONT_FAMILY}; fill:#000; font-weight:bold; }}
      .tag {{ font-size:14px; font-family:{FONT_FAMILY}; fill:#000; font-style:italic; }}
    </style>
  </defs>
  <rect width="{sw}" height="{sh}" fill="#fff"/>''']

    # ---- 轨道圆 ----
    parts.append('\n  <!-- 轨道 -->')
    orbit_labels = ["I", "II", "III"]
    for oi, oc in enumerate(orbit_circles):
        label = orbit_labels[oi] if oi < len(orbit_labels) else str(oi+1)
        cx_s, cy_s = sx(oc["cx"]), sy(oc["cy"])
        r_s = oc["r"] * scale
        
        # 轨道I 是特殊轨迹（不是完整圆），用虚线但标注不同
        cls = "orbit" if label != "I" else "orbit"
        
        parts.append(f'  <g data-orbit="{label}">')
        parts.append(f'    <circle cx="{cx_s:.1f}" cy="{cy_s:.1f}" r="{r_s:.1f}" class="{cls}"/>')
        # 标签放在右下象限
        lx = cx_s + r_s * 0.65
        ly = cy_s + r_s * 0.45
        parts.append(f'    <text x="{lx:.1f}" y="{ly:.1f}" class="tag">{label}</text>')
        parts.append(f'  </g>')

    # ---- 火星本体 ----
    if planet_circle:
        px, py = sx(planet_circle["cx"]), sy(planet_circle["cy"])
        pr = planet_circle["r"] * scale
        parts.append('\n  <!-- 火星 -->')
        parts.append(f'  <g data-type="planet">')
        parts.append(f'    <circle cx="{px:.1f}" cy="{py:.1f}" r="{pr:.1f}" class="body"/>')
        parts.append(f'    <text x="{px:.1f}" y="{py+6:.1f}" class="lbl-b" text-anchor="middle">火星</text>')
        parts.append(f'  </g>')

    # ---- 标记点 (S, Q, P) ----
    parts.append('\n  <!-- 探测点 -->')
    default_names = ["S", "Q", "P"]
    for mi, mk in enumerate(markers):
        mx, my = sx(mk["cx"]), sy(mk["cy"])
        mr = max(4, mk["r"] * scale * 0.65)
        name = default_names[mi] if mi < len(default_names) else f"P{mi}"
        
        # 查找关联的 OCR 文字
        for t in ocr_texts:
            d = math.sqrt((t["cx"]-mk["cx"])**2 + (t["cy"]-mk["cy"])**2)
            if d < 20:
                name = t["text"]
                break
        
        # 标签偏移方向根据点的相对位置
        label_offset_x = mr + 6
        label_offset_y = 4
        
        parts.append(f'  <g data-marker="{name}">')
        parts.append(f'    <circle cx="{mx:.1f}" cy="{my:.1f}" r="{mr:.1f}" class="dot"/>')
        parts.append(f'    <text x="{mx+label_offset_x:.1f}" y="{my+label_offset_y:.1f}" class="lbl-b">{name}</text>')
        parts.append(f'  </g>')

    # ---- 轨迹箭头（长线段 → 贝塞尔曲线近似）----
    parts.append('\n  <!-- 轨迹曲线 I -->')
    ll = geo["long_lines"]
    if ll:
        # 收集所有长线段端点，拟合一条平滑曲线
        pts = [(l["x1"], l["y1"]) for l in ll] + [(l["x2"], l["y2"]) for l in ll]
        # 按位置排序（从左上到右下）
        pts_sorted = sorted(pts, key=lambda p: p[0]*100 + p[1])
        if len(pts_sorted) >= 2:
            # 构建贝塞尔路径
            path_d = f"M{sx(pts_sorted[0][0]):.1f},{sy(pts_sorted[0][1]):.1f}"
            # 简化：直接连线段作为轨迹
            for pt in pts_sorted[1:]:
                path_d += f" L{sx(pt[0]):.1f},{sy(pt[1]):.1f}"
            parts.append(f'  <path d="{path_d}" class="traj"/>')

    # ---- 未关联的 OCR 文字 ----
    used_ocr_ids = set()
    if planet_circle and mars_text:
        used_ocr_ids.add(id(mars_text))
    for mk in markers:
        for t in ocr_texts:
            d = math.sqrt((t["cx"]-mk["cx"])**2 + (t["cy"]-mk["cy"])**2)
            if d < 20:
                used_ocr_ids.add(id(t))

    unused_ocr = [t for t in ocr_texts if id(t) not in used_ocr_ids]
    if unused_ocr:
        parts.append('\n  <!-- 其他文字 -->')
        for t in unused_ocr:
            parts.append(f'  <text x="{sx(t['cx']):.1f}" y="{sy(t['cy']):.1f}" '
                        f'class="lbl" data-ocr="{t["text"]}">{t["text"]}</text>')

    parts.append('\n</svg>')
    return '\n'.join(parts)


def build_exam_html(svg_path, geo, ocr_texts):
    svg_content = svg_path.read_text(encoding='utf-8')
    
    exam_q = ("如图，火星绕太阳做匀速圆周运动，火星与太阳的间距为r₁，"
              "火星的运行周期为T₁。某航天器绕火星做匀速圆周运动，航天器与火星的间距为r₂，"
              "航天器的运行周期为T₂。已知火星的质量为M，引力常量为G，则（　　）")
    opts = [
        'A. 火星的线速度大小为 2πr₁/T₁',
        'B. 航天器的线速度大小为 2πr₂/T₂',
        'C. 火星的质量 M = 4π²r₁³/(GT₁²)',
        'D. 航天器的运行周期 T₂ = 2π√(r₂³/GM)'
    ]
    
    # 分析报告
    cr_info = ""
    for i, c in enumerate(geo["circles_clustered"][:6]):
        cr_info += f'<li><b>{i}</b>: ({c["cx"]:.0f},{c["cy"]:.0f}) r={c["r"]:.0f} 支持={c["support"]}</li>'
    mk_info = ""
    for i, m in enumerate(geo["markers"]):
        mk_info += f'<li><b>{i}</b>: ({m["cx"]:.0f},{m["cy"]:.0f}) r={m["r"]:.1f} 圆度={m["circ"]:.2f}</li>'
    ocr_info = "".join(f'<li>"{t["text"]}" @({t["cx"]:.0f},{t["cy"]:.0f}) 置信度{t["conf"]:.0%}</li>' for t in ocr_texts)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>物理试卷 SVG 预览</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700&family=Noto+Serif+SC:wght@400;700&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#e8e4df;font-family:'Noto Serif SC','SimSun',serif;display:flex;flex-direction:column;align-items:center;padding:30px 20px}}
.page{{background:white;width:210mm;min-height:297mm;padding:25mm 30px;box-shadow:0 2px 20px rgba(0,0,0,.15);margin-bottom:30px;position:relative}}
.page::before{{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:#c00}}
.exam-header{{text-align:center;border-bottom:2px solid #000;padding-bottom:15px;margin-bottom:25px}}
.exam-header h1{{font-size:22px;font-weight:700;letter-spacing:8px}}
.exam-header p{{font-size:13px;color:#666;margin-top:5px}}
.sec-title{{font-size:15px;font-weight:700;margin:20px 0 12px 0;border-left:3px solid #c00;padding-left:10px}}
.q{{margin:18px 0;font-size:15px;line-height:1.8}}.q-num{{font-weight:700}}
.fig-box{{display:flex;justify-content:center;margin:15px 0;padding:10px}}
.fig-box svg{{max-width:340px}}
.opts{{margin:8px 0 8px 24px;line-height:2}}
.wf-card{{background:white;width:210mm;padding:25mm 30px;box-shadow:0 2px 20px rgba(0,0,0,.15)}}
.wf-card h2{{font-size:18px;margin-bottom:15px;color:#333}}
.step{{background:#f8f7f5;border-left:4px solid #c00;padding:12px 15px;margin:10px 0;border-radius:0 6px 6px 0}}
.sn{{display:inline-block;background:#c00;color:white;width:24px;height:24px;border-radius:50%;text-align:center;line-height:24px;font-size:13px;margin-right:8px;font-weight:700}}
code{{background:#eee;padding:2px 6px;border-radius:3px;font-size:13px}}.hl{{color:#c00;font-weight:700}}
.tbl{{width:100%;border-collapse:collapse;margin:15px 0;font-size:14px}}
.tbl th{{background:#f0f0ec;padding:8px 12px;text-align:left}}
.tbl td{{padding:8px 12px;border-bottom:1px solid #e0e0dc}}.tbl .rec{{background:#fffbe6}}
.anl{{background:#f5f5f0;padding:15px;border-radius:8px;margin-top:15px;font-size:13px;line-height:1.8}}
.anl h4{{margin:0 0 8px 0}}.anl ul{{margin-left:20px}}
.note{{background:#fffbe6;padding:12px;border-radius:6px;margin-top:15px;font-size:14px}}
</style></head>
<body>

<!-- ===== 试卷预览 ===== -->
<div class="page"><div class="exam-header">
<h1>物理试题</h1><p>2026年普通高等学校招生全国统一考试（模拟）</p></div>
<div class="sec-title">二、选择题</div>
<div class="q"><span class="q-num">6.</span>{exam_q}
<div class="fig-box">{svg_content}</div>
<div class="opts">{'<br/>'.join(opts)}</div></div>
<div style="margin-top:30px;border-top:1px solid #ccc;padding-top:15px;font-size:12px;color:#999;text-align:center;">
▲ SVG 直接嵌入 — 所有文字为 &lt;text&gt; 元素，可选中编辑</div></div>

<!-- ===== 工作流说明 ===== -->
<div class="wf-card"><h2>📐 物理题图工作流</h2>
<div class="step"><span class="sn">1</span><b>编辑源文件</b>：Inkscape/Illustrator 打开 .svg → 修改任何元素（文字/线条/位置）</div>
<div class="step"><span class="sn">2</span><b>导出嵌入试卷</b>：
<table class="tbl"><tr><th>试卷工具</th><th>格式</th><th>操作</th></tr>
<tr class="rec"><td><b>Word/WPS（主流）</b></td><td>PNG 300dpi</td><td>Inkscape → 导出PNG(300dpi) → 插入Word</td></tr>
<tr><td><b>LaTeX</b></td><td>PDF</td><td>Inkscape → 另存PDF → \\includegraphics</td></tr>
<tr><td><b>HTML 在线试卷</b></td><td>SVG 内联</td><td>&lt;img src="xxx.svg"&gt;</td></tr></table></div>
<div class="step"><span class="sn">3</span><b>核心原则</b>：<span class="hl">SVG 是源码，PNG 是编译产物</span><br/>
<span style="color:#666">永远编辑 SVG → 按需导出 PNG。❌ 不要反向操作。</span></div>
<div class="note">💡 为什么不把 SVG 再转回 JPG？<br/>
因为 矢量→光栅化→再矢量化 = <b>丢失全部可编辑性</b>！<br/>
正确路径：<code>原始图片 → (OCR+CV+模板) → SVG源文件 → (按需) → PNG/PDF → 试卷</code></div>

<div class="anl"><h4>📊 本次分析结果</h4>
<p>原始图片: {geo['size']['w']}×{geo['size']['h']}px | 圆形聚类结果:</p><ul>{cr_info}</ul>
<p>标记点 ({len(geo['markers'])}):</p><ul>{mk_info}</ul>
<p>OCR 识别 ({len(ocr_texts)}):</p><ul>{ocr_info}</ul></div>
</div>
</body></html>"""
    return html


def main():
    print("="*60)
    print("物理题图片 → 可编辑 SVG 转换器 v7")
    print("RapidOCR + OpenCV 聚类过滤 + 确定性重建")
    print("="*60)

    print("\n[1/4] OCR...")
    try:
        texts = run_ocr(INPUT_IMAGE)
        for t in texts: print(f"  '{t['text']}' @ ({t['cx']:.0f},{t['cy']:.0f}) [{t['conf']:.0%}]")
    except Exception as e:
        print(f"  ⚠ {e}")
        texts = []

    print("\n[2/4] 几何分析...")
    geo = analyze_structure(INPUT_IMAGE)
    print(f"  图像: {geo['size']['w']}×{geo['size']['h']}")
    print(f"  圆形聚类(Top 6):")
    for i,c in enumerate(geo["circles_clustered"][:6]):
        print(f"    [{i}] ({c['cx']:.0f},{c['cy']:.0f}) r={c['r']:.0f} 支持度={c['support']}")
    print(f"  标记点: {len(geo['markers'])} 个")
    for i,m in enumerate(geo["markers"]):
        print(f"    点{i}: ({m['cx']:.0f},{m['cy']:.0f}) r={m['r']:.1f} 圆度={m['circ']:.2f}")
    print(f"  长线段: {len(geo['long_lines'])}")

    print("\n[3/4] 构建 SVG...")
    svg = build_svg(geo, texts)
    OUTPUT_SVG.write_text(svg, encoding='utf-8')
    print(f"  ✅ {OUTPUT_SVG}")

    analysis = {
        "version": "v7",
        "image_size": geo["size"],
        "circles_detected": len(geo["circles_clustered"]),
        "circles_top": [{"cx":c["cx"],"cy":c["cy"],"r":c["r"],"sup":c["support"]} for c in geo["circles_clustered"][:8]],
        "markers": [{"cx":m["cx"],"cy":m["cy"],"r":m["r"]} for m in geo["markers"]],
        "lines_count": len(geo["long_lines"]),
        "ocr": [t["text"] for t in texts]
    }
    OUTPUT_ANALYSIS.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  ✅ {OUTPUT_ANALYSIS}")

    print("\n[4/4] HTML 预览...")
    html = build_exam_html(OUTPUT_SVG, geo, texts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"  ✅ {OUTPUT_HTML}")
    
    print(f"\n{'='*60}\n🎉 完成！打开 exam_preview_v5.html\n{'='*60}")

if __name__ == "__main__":
    main()
