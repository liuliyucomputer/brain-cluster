"""
物理题图片 → 可编辑 SVG 转换器 v5
=====================================
完整 pipeline:
  1. RapidOCR 自动识别中文/英文标签
  2. OpenCV 检测圆形、线段、点
  3. 线段聚类合并（虚线→整圆弧）
  4. 生成试卷风格可编辑 SVG
  5. 同时导出 SVG 源文件 + PNG 试卷嵌入版
"""

import cv2
import numpy as np
from pathlib import Path
import json
import math
import sys

# ============================================================
# 配置
# ============================================================
INPUT_IMAGE = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUTPUT_DIR = Path(r"D:\brain\eyes\SVG")
OUTPUT_SVG = OUTPUT_DIR / "physics_auto_final.svg"
OUTPUT_PNG = OUTPUT_DIR / "physics_auto_final.png"
OUTPUT_ANALYSIS = OUTPUT_DIR / "analysis_v5.json"
OUTPUT_HTML = OUTPUT_DIR / "exam_preview_v5.html"

# 试卷风格参数
FONT_FAMILY = "Noto Sans SC, SimSun, serif"
STROKE_COLOR = "#000000"
FILL_WHITE = "#FFFFFF"
DASH_PATTERN = "5,3"
LINE_WIDTH = 1.5
ARROW_SIZE = 8
LABEL_FONT_SIZE = 16
SMALL_LABEL_SIZE = 14

# ============================================================
# Step 1: OCR 文字识别
# ============================================================
def run_ocr(image_path: str) -> list:
    """用 RapidOCR 识别图中文字，返回 [{text, bbox, confidence}]"""
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    result, _ = ocr(image_path)

    texts = []
    if result:
        for item in result:
            bbox, text, confidence = item
            # bbox: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            cx = sum(x_coords) / 4
            cy = sum(y_coords) / 4
            w = max(x_coords) - min(x_coords)
            h = max(y_coords) - min(y_coords)
            texts.append({
                "text": text,
                "bbox": bbox,
                "cx": cx,
                "cy": cy,
                "w": w,
                "h": h,
                "confidence": float(confidence)
            })
    return texts

# ============================================================
# Step 2: 几何检测
# ============================================================
def detect_geometry(image_path: str):
    """检测圆形、线段、箭头端点"""
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")
    
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 二值化
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # --- 检测圆形 ---
    circles = []
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    det_circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=30,
        param1=50, param2=30, minRadius=10, maxRadius=min(h, w) // 2
    )
    if det_circles is not None:
        for c in det_circles[0]:
            x, y, r = c
            circles.append({"cx": float(x), "cy": float(y), "r": float(r)})
    
    # --- 检测线段 ---
    edges = cv2.Canny(gray, 50, 150)
    lines_raw = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=20,
        minLineLength=8, maxLineGap=6
    )
    lines = []
    if lines_raw is not None:
        for l in lines_raw:
            x1, y1, x2, y2 = l[0]
            length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            angle = math.degrees(math.atan2(y2-y1, x2-x1))
            lines.append({
                "x1": float(x1), "y1": float(y1),
                "x2": float(x2), "y2": float(y2),
                "length": length, "angle": angle
            })
    
    # --- 检测填充点（小实心圆）---
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    points = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 3 < area < 80:
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                points.append({"cx": float(cx), "cy": float(cy), "area": float(area)})
    
    return {
        "image_size": {"w": w, "h": h},
        "circles": circles,
        "lines": lines,
        "points": points
    }

# ============================================================
# Step 3: 智能聚类 — 将虚线段合并为圆弧
# ============================================================
def cluster_lines_to_arcs(lines: list, circles: list) -> dict:
    """
    根据圆形检测结果，将线段分配到对应圆弧组。
    返回 {circle_idx: [lines]} + 孤立线段
    """
    arc_groups = {}
    used = set()
    
    for ci, circle in enumerate(circles):
        cx, cy, r = circle["cx"], circle["cy"], circle["r"]
        group = []
        for li, line in enumerate(lines):
            if li in used:
                continue
            # 线段中点到圆心距离与半径的差距
            mid_x = (line["x1"] + line["x2"]) / 2
            mid_y = (line["y1"] + line["y2"]) / 2
            dist_to_center = math.sqrt((mid_x - cx)**2 + (mid_y - cy)**2)
            if abs(dist_to_center - r) < max(r * 0.3, 15):
                group.append(line)
                used.add(li)
        if group:
            arc_groups[ci] = group
    
    # 剩余未归组的线段
    standalone = [lines[i] for i in range(len(lines)) if i not in used]
    
    return arc_groups, standalone

# ============================================================
# Step 4: 智能标签关联 — OCR 文字与几何元素配对
# ============================================================
def associate_labels(texts: list, circles: list, points: list) -> dict:
    """将 OCR 文字标签分配到最近的几何元素"""
    labels = {
        "circles": {},  # circle_idx -> text
        "points": {},   # point_idx -> text
        "unassigned": []
    }
    
    used_texts = set()
    
    # 圆形标签：找最近的文字
    for ci, circle in enumerate(circles):
        best_ti = None
        best_dist = float('inf')
        for ti, text in enumerate(texts):
            if ti in used_texts:
                continue
            dist = math.sqrt((text["cx"] - circle["cx"])**2 + (text["cy"] - circle["cy"])**2)
            # 标签应该在圆的边缘或附近
            edge_dist = abs(dist - circle["r"])
            if edge_dist < circle["r"] * 0.5 and edge_dist < best_dist:
                best_dist = edge_dist
                best_ti = ti
        if best_ti is not None:
            labels["circles"][ci] = texts[best_ti]
            used_texts.add(best_ti)
    
    # 点标签：找最近的文字
    for pi, point in enumerate(points):
        best_ti = None
        best_dist = float('inf')
        for ti, text in enumerate(texts):
            if ti in used_texts:
                continue
            dist = math.sqrt((text["cx"] - point["cx"])**2 + (text["cy"] - point["cy"])**2)
            if dist < 40 and dist < best_dist:
                best_dist = dist
                best_ti = ti
        if best_ti is not None:
            labels["points"][pi] = texts[best_ti]
            used_texts.add(best_ti)
    
    # 未分配的文字
    for ti, text in enumerate(texts):
        if ti not in used_texts:
            labels["unassigned"].append(text)
    
    return labels

# ============================================================
# Step 5: SVG 生成 — 试卷风格
# ============================================================
def generate_exam_svg(geo: dict, texts: list, arc_groups: dict, 
                      standalone_lines: list, labels: dict) -> str:
    """生成试卷风格的可编辑 SVG"""
    iw = geo["image_size"]["w"]
    ih = geo["image_size"]["h"]
    margin = 20
    svg_w = iw + margin * 2
    svg_h = ih + margin * 2
    
    parts = []
    parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{svg_w}" height="{svg_h}" 
     viewBox="0 0 {svg_w} {svg_h}"
     style="background: white;">
  <defs>
    <marker id="arrowhead" markerWidth="{ARROW_SIZE}" markerHeight="{ARROW_SIZE}" 
            refX="{ARROW_SIZE-1}" refY="{ARROW_SIZE/2}" orient="auto">
      <polygon points="0 0, {ARROW_SIZE} {ARROW_SIZE/2}, 0 {ARROW_SIZE}" 
               fill="{STROKE_COLOR}"/>
    </marker>
    <marker id="arrowhead-red" markerWidth="{ARROW_SIZE}" markerHeight="{ARROW_SIZE}" 
            refX="{ARROW_SIZE-1}" refY="{ARROW_SIZE/2}" orient="auto">
      <polygon points="0 0, {ARROW_SIZE} {ARROW_SIZE/2}, 0 {ARROW_SIZE}" 
               fill="#CC0000"/>
    </marker>
    <style>
      .orbit {{ stroke: {STROKE_COLOR}; fill: none; stroke-dasharray: {DASH_PATTERN}; stroke-width: {LINE_WIDTH}; }}
      .solid-line {{ stroke: {STROKE_COLOR}; fill: none; stroke-width: {LINE_WIDTH}; }}
      .arrow-line {{ stroke: {STROKE_COLOR}; fill: none; stroke-width: {LINE_WIDTH}; marker-end: url(#arrowhead); }}
      .arrow-red {{ stroke: #CC0000; fill: none; stroke-width: 2; marker-end: url(#arrowhead-red); }}
      .label {{ font-size: {LABEL_FONT_SIZE}px; font-family: {FONT_FAMILY}; fill: {STROKE_COLOR}; }}
      .label-small {{ font-size: {SMALL_LABEL_SIZE}px; font-family: {FONT_FAMILY}; fill: {STROKE_COLOR}; }}
      .dot {{ fill: {STROKE_COLOR}; }}
      .body {{ fill: {FILL_WHITE}; stroke: {STROKE_COLOR}; stroke-width: {LINE_WIDTH}; }}
    </style>
  </defs>
  
  <!-- 背景 -->
  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="white"/>''')

    ox, oy = margin, margin  # offset
    
    # --- 圆形轨道 ---
    parts.append('\n  <!-- 轨道圆 -->')
    for ci, circle in enumerate(geo["circles"]):
        cx = circle["cx"] + ox
        cy = circle["cy"] + oy
        r = circle["r"]
        
        # 判断是否为轨道（根据半径排序）
        is_orbit = r > 30  # 小圆是星球本体
        
        if is_orbit:
            # 检查这个圆有没有被线段组覆盖（有→虚线轨道，没有→实线圆）
            has_arc = ci in arc_groups and len(arc_groups[ci]) > 3
            if has_arc:
                parts.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="orbit" data-type="orbit" data-idx="{ci}"/>')
            else:
                parts.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="orbit" data-type="orbit" data-idx="{ci}"/>')
        else:
            # 星球本体
            parts.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="body" data-type="planet" data-idx="{ci}"/>')
        
        # 圆形标签
        if ci in labels["circles"]:
            lbl = labels["circles"][ci]
            # 标签放在圆心
            parts.append(f'  <text x="{cx:.1f}" y="{cy+5:.1f}" class="label" text-anchor="middle" data-ocr="{lbl["text"]}">{lbl["text"]}</text>')
    
    # --- 孤立线段（轨迹曲线、箭头等）---
    parts.append('\n  <!-- 独立线段 -->')
    for li, line in enumerate(standalone_lines):
        x1, y1 = line["x1"] + ox, line["y1"] + oy
        x2, y2 = line["x2"] + ox, line["y2"] + oy
        length = line["length"]
        angle = line["angle"]
        
        # 短线段可能是箭头的一部分，长线段是轨迹
        if length > 25:
            # 可能是曲线轨迹的一部分，用实线
            parts.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="arrow-red" data-type="trajectory"/>')
        else:
            parts.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="solid-line" data-type="line"/>')
    
    # --- 点 ---
    parts.append('\n  <!-- 标记点 -->')
    for pi, point in enumerate(geo["points"]):
        cx = point["cx"] + ox
        cy = point["cy"] + oy
        r = max(2, min(5, math.sqrt(point["area"]) / 2))
        parts.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="dot" data-type="point" data-idx="{pi}"/>')
        
        # 点标签
        if pi in labels["points"]:
            lbl = labels["points"][pi]
            parts.append(f'  <text x="{cx+8:.1f}" y="{cy+5:.1f}" class="label" data-ocr="{lbl["text"]}">{lbl["text"]}</text>')
    
    # --- 未分配的 OCR 文字 ---
    parts.append('\n  <!-- OCR 识别文字（未关联几何元素）-->')
    for ti, text in enumerate(labels["unassigned"]):
        cx = text["cx"] + ox
        cy = text["cy"] + oy
        parts.append(f'  <text x="{cx:.1f}" y="{cy:.1f}" class="label-small" data-ocr="{text["text"]}" data-conf="{text["confidence"]:.2f}">{text["text"]}</text>')
    
    parts.append('\n</svg>')
    return '\n'.join(parts)

# ============================================================
# Step 6: 生成试卷嵌入 HTML 预览
# ============================================================
def generate_exam_html(svg_path: Path, png_path: Path, geo: dict, texts: list) -> str:
    """生成模拟物理试卷 HTML，展示 SVG 直接嵌入 + PNG 嵌入两种方式"""
    
    svg_content = svg_path.read_text(encoding='utf-8')
    
    # 试卷题目文本
    exam_question = """如图，火星绕太阳做匀速圆周运动，火星与太阳的间距为r₁，火星的运行周期为T₁。某航天器绕火星做匀速圆周运动，航天器与火星的间距为r₂，航天器的运行周期为T₂。已知火星的质量为M，引力常量为G，则（　　）"""
    
    exam_options = [
        "A. 火星的线速度大小为 2πr₁/T₁",
        "B. 航天器的线速度大小为 2πr₂/T₂",
        "C. 火星的质量 M = 4π²r₁³/(GT₁²)",
        "D. 航天器的运行周期 T₂ = 2π√(r₂³/GM)"
    ]
    
    # 分析报告
    analysis_html = ""
    analysis_path = OUTPUT_DIR / "analysis_v5.json"
    if analysis_path.exists():
        analysis_data = json.loads(analysis_path.read_text(encoding='utf-8'))
        analysis_html = f"""
        <div style="background:#f5f5f0; padding:15px; border-radius:8px; margin-top:20px; font-size:14px;">
          <h4 style="margin:0 0 10px 0;">📊 图像分析结果</h4>
          <p>检测到 <b>{len(geo.get('circles',[]))}</b> 个圆形，<b>{len(geo.get('lines',[]))}</b> 条线段，<b>{len(geo.get('points',[]))}</b> 个标记点</p>
          <p>OCR 识别到 <b>{len(texts)}</b> 个文字区域：</p>
          <ul>{chr(10).join(f'<li><code>{t["text"]}</code> (置信度: {t["confidence"]:.1%})</li>' for t in texts)}</ul>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>物理试卷 SVG 嵌入预览</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700&family=Noto+Serif+SC:wght@400;700&display=swap');
  
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  
  body {{ 
    background: #e8e4df; 
    font-family: 'Noto Serif SC', 'SimSun', serif;
    display: flex; flex-direction: column; align-items: center;
    padding: 30px 20px;
  }}
  
  .page {{
    background: white;
    width: 210mm; min-height: 297mm;
    padding: 25mm 30mm;
    box-shadow: 0 2px 20px rgba(0,0,0,0.15);
    margin-bottom: 30px;
    position: relative;
  }}
  
  .page::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0;
    height: 4px; background: #c00;
  }}
  
  .exam-header {{
    text-align: center;
    border-bottom: 2px solid #000;
    padding-bottom: 15px;
    margin-bottom: 25px;
  }}
  .exam-header h1 {{ font-size: 22px; font-weight: 700; letter-spacing: 8px; }}
  .exam-header p {{ font-size: 13px; color: #666; margin-top: 5px; }}
  
  .section-title {{
    font-size: 15px; font-weight: 700;
    margin: 20px 0 12px 0;
    border-left: 3px solid #c00;
    padding-left: 10px;
  }}
  
  .question {{
    margin: 18px 0;
    font-size: 15px;
    line-height: 1.8;
  }}
  .question .q-num {{ font-weight: 700; }}
  
  .figure-container {{
    display: flex;
    justify-content: center;
    margin: 15px 0;
    padding: 10px;
  }}
  .figure-container svg {{
    max-width: 280px;
  }}
  
  .options {{
    margin: 8px 0 8px 24px;
    line-height: 2;
  }}
  
  .answer-blank {{
    display: inline-block;
    width: 120px;
    border-bottom: 1px solid #000;
    margin: 0 5px;
  }}
  
  /* 工作流说明卡片 */
  .workflow-card {{
    background: white;
    width: 210mm;
    padding: 25mm 30mm;
    box-shadow: 0 2px 20px rgba(0,0,0,0.15);
  }}
  .workflow-card h2 {{ font-size: 18px; margin-bottom: 15px; color: #333; }}
  .workflow-card .step {{
    background: #f8f7f5;
    border-left: 4px solid #c00;
    padding: 12px 15px;
    margin: 10px 0;
    border-radius: 0 6px 6px 0;
  }}
  .workflow-card .step .step-num {{ 
    display: inline-block; background: #c00; color: white;
    width: 24px; height: 24px; border-radius: 50%;
    text-align: center; line-height: 24px; font-size: 13px;
    margin-right: 8px; font-weight: 700;
  }}
  .workflow-card code {{ background: #eee; padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
  .workflow-card .highlight {{ color: #c00; font-weight: 700; }}
  
  .method-compare {{
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 14px;
  }}
  .method-compare th {{ background: #f0f0ec; padding: 8px 12px; text-align: left; }}
  .method-compare td {{ padding: 8px 12px; border-bottom: 1px solid #e0e0dc; }}
  .method-compare .recommended {{ background: #fffbe6; }}
</style>
</head>
<body>

<!-- ============================================ -->
<!-- 试卷预览 -->
<!-- ============================================ -->
<div class="page">
  <div class="exam-header">
    <h1>物理试题</h1>
    <p>2026 年普通高等学校招生全国统一考试（模拟）</p>
  </div>
  
  <div class="section-title">二、选择题：本题共 8 小题，每小题 6 分，共 48 分。</div>
  
  <div class="question">
    <span class="q-num">6.</span> {exam_question}
    
    <div class="figure-container">
      {svg_content}
    </div>
    
    <div class="options">
      {'<br/>'.join(exam_options)}
    </div>
  </div>
  
  <div style="margin-top: 40px; border-top: 1px solid #ccc; padding-top: 15px; font-size: 13px; color: #999; text-align: center;">
    ▲ 以上为 SVG 直接嵌入试卷的效果 — 所有文字可直接选中编辑
  </div>
</div>

<!-- ============================================ -->
<!-- 工作流说明 -->
<!-- ============================================ -->
<div class="workflow-card">
  <h2>📐 SVG 在物理试卷中的工作流</h2>
  
  <div class="step">
    <span class="step-num">1</span>
    <b>编辑源文件</b>：用 Inkscape / Illustrator 打开 <code>.svg</code> 文件，修改任何元素（文字、线条、位置）
  </div>
  
  <div class="step">
    <span class="step-num">2</span>
    <b>导出为试卷格式</b>：
    <table class="method-compare">
      <tr><th>试卷工具</th><th>嵌入方式</th><th>操作</th></tr>
      <tr class="recommended">
        <td><b>Word / WPS</b></td>
        <td>PNG (300dpi)</td>
        <td>Inkscape: 文件 → 导出PNG → 分辨率 300dpi → 插入Word</td>
      </tr>
      <tr>
        <td><b>LaTeX</b></td>
        <td>PDF</td>
        <td>Inkscape: 文件 → 另存为 PDF → <code>\\includegraphics</code></td>
      </tr>
      <tr>
        <td><b>HTML 在线试卷</b></td>
        <td>SVG 直接嵌入</td>
        <td>直接 <code>&lt;img src="xxx.svg"&gt;</code> 或内联</td>
      </tr>
    </table>
  </div>
  
  <div class="step">
    <span class="step-num">3</span>
    <b>核心原则</b>：<span class="highlight">SVG 是源码，PNG 是编译产物</span>。永远编辑 SVG，需要时导出 PNG。不要反向操作！
  </div>
  
  <div style="background:#fffbe6; padding:12px; border-radius:6px; margin-top:15px; font-size:14px;">
    💡 <b>为什么不用 SVG→JPG 再转回？</b> 因为 SVG 矢量图 → JPG 光栅化 → 再转 SVG = 丢失所有可编辑性！<br/>
    正确路径是：<code>原始图片 → (OCR+CV) → SVG源文件 → (按需导出) → PNG/PDF</code>
  </div>
  
  {analysis_html}
</div>

</body>
</html>"""
    return html

# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("物理题图片 → 可编辑 SVG 转换器 v5")
    print("=" * 60)
    
    # Step 1: OCR
    print("\n[Step 1/5] OCR 文字识别...")
    try:
        texts = run_ocr(INPUT_IMAGE)
        print(f"  识别到 {len(texts)} 个文字区域:")
        for t in texts:
            print(f"    '{t['text']}' (置信度: {t['confidence']:.1%}) @ ({t['cx']:.0f}, {t['cy']:.0f})")
    except Exception as e:
        print(f"  ⚠ OCR 失败: {e}")
        texts = []
    
    # Step 2: 几何检测
    print("\n[Step 2/5] 几何元素检测...")
    geo = detect_geometry(INPUT_IMAGE)
    print(f"  图片尺寸: {geo['image_size']['w']}x{geo['image_size']['h']}")
    print(f"  检测到 {len(geo['circles'])} 个圆形:")
    for i, c in enumerate(geo["circles"]):
        print(f"    圆{i}: 中心({c['cx']:.0f},{c['cy']:.0f}) 半径={c['r']:.0f}")
    print(f"  检测到 {len(geo['lines'])} 条线段")
    print(f"  检测到 {len(geo['points'])} 个标记点")
    
    # Step 3: 线段聚类
    print("\n[Step 3/5] 线段聚类...")
    arc_groups, standalone = cluster_lines_to_arcs(geo["lines"], geo["circles"])
    print(f"  {len(arc_groups)} 个圆弧组:")
    for ci, group in arc_groups.items():
        print(f"    圆{ci}: {len(group)} 条线段归入")
    print(f"  {len(standalone)} 条独立线段")
    
    # Step 4: 标签关联
    print("\n[Step 4/5] 标签关联...")
    labels = associate_labels(texts, geo["circles"], geo["points"])
    for ci, lbl in labels["circles"].items():
        print(f"  圆{ci} → '{lbl['text']}'")
    for pi, lbl in labels["points"].items():
        print(f"  点{pi} → '{lbl['text']}'")
    for t in labels["unassigned"]:
        print(f"  未分配: '{t['text']}' @ ({t['cx']:.0f},{t['cy']:.0f})")
    
    # Step 5: 生成 SVG
    print("\n[Step 5/5] 生成试卷风格 SVG...")
    svg_content = generate_exam_svg(geo, texts, arc_groups, standalone, labels)
    OUTPUT_SVG.write_text(svg_content, encoding='utf-8')
    print(f"  ✅ SVG 已保存: {OUTPUT_SVG}")
    
    # 导出 PNG
    try:
        import cairosvg
        cairosvg.svg2png(url=str(OUTPUT_SVG), write_to=str(OUTPUT_PNG), dpi=300)
        print(f"  ✅ PNG 已导出: {OUTPUT_PNG}")
    except ImportError:
        # 用 OpenCV 渲染 SVG 为位图（简化版）
        print("  ⚠ cairosvg 未安装，跳过 PNG 导出（可用 Inkscape 命令行导出）")
    
    # 保存分析数据
    analysis = {
        "image": INPUT_IMAGE,
        "image_size": geo["image_size"],
        "ocr_texts": texts,
        "circles": geo["circles"],
        "lines_count": len(geo["lines"]),
        "points_count": len(geo["points"]),
        "arc_groups": {str(k): len(v) for k, v in arc_groups.items()},
        "standalone_lines": len(standalone),
        "labels": {
            "circles": {str(k): v["text"] for k, v in labels["circles"].items()},
            "points": {str(k): v["text"] for k, v in labels["points"].items()},
            "unassigned": [t["text"] for t in labels["unassigned"]]
        }
    }
    OUTPUT_ANALYSIS.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  ✅ 分析数据已保存: {OUTPUT_ANALYSIS}")
    
    # 生成预览 HTML
    print("\n生成试卷预览页...")
    html = generate_exam_html(OUTPUT_SVG, OUTPUT_PNG, geo, texts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"  ✅ 预览页已保存: {OUTPUT_HTML}")
    
    print("\n" + "=" * 60)
    print("🎉 完成！查看 exam_preview_v5.html 查看试卷效果")
    print("=" * 60)

if __name__ == "__main__":
    main()
