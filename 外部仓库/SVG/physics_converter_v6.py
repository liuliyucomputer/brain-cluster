"""
物理题图片 → 可编辑 SVG 转换器 v6
=====================================
核心策略：OCR 自动识别文字 + 图像分析提取几何参数 + 智能重建
不再逐像素检测，而是：
  1. OCR 提取所有文字标签及位置
  2. 图像分析提取关键几何参数（圆形、线段方向）
  3. 用确定性模板重建高质量 SVG
  4. 同时输出 SVG + 试卷嵌入 HTML
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
OUTPUT_SVG = OUTPUT_DIR / "physics_auto_final.svg"
OUTPUT_ANALYSIS = OUTPUT_DIR / "analysis_v6.json"
OUTPUT_HTML = OUTPUT_DIR / "exam_preview_v5.html"

FONT_FAMILY = "Noto Sans SC, SimSun, serif"

# ============================================================
# Step 1: OCR
# ============================================================
def run_ocr(image_path: str) -> list:
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    result, _ = ocr(image_path)
    texts = []
    if result:
        for item in result:
            bbox, text, confidence = item
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            cx = sum(x_coords) / 4
            cy = sum(y_coords) / 4
            texts.append({
                "text": text,
                "cx": float(cx), "cy": float(cy),
                "w": float(max(x_coords) - min(x_coords)),
                "h": float(max(y_coords) - min(y_coords)),
                "confidence": float(confidence)
            })
    return texts

# ============================================================
# Step 2: 智能图像分析 — 提取结构参数
# ============================================================
def analyze_image_structure(image_path: str) -> dict:
    """从图片中提取关键几何结构参数"""
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"无法读取: {image_path}")
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # --- 检测圆形（用更宽松的参数 + 过滤）---
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    circles_raw = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=20,
        param1=60, param2=25, minRadius=8, maxRadius=min(h, w) // 2
    )
    
    # 去除重叠圆
    circles = []
    if circles_raw is not None:
        sorted_circles = sorted(circles_raw[0], key=lambda c: c[2], reverse=True)
        for c in sorted_circles:
            x, y, r = c
            # 检查是否被已选的大圆包含
            is_contained = False
            for sc in circles:
                dist = math.sqrt((x - sc[0])**2 + (y - sc[1])**2)
                if dist < sc[2] * 0.5:  # 中心在大圆内
                    is_contained = True
                    break
            if not is_contained:
                circles.append((float(x), float(y), float(r)))
    
    # --- 检测实心黑点（标记点 S/Q/P）---
    _, binary = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    # 形态学操作：只保留小圆点
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small)
    kernel_big = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_big)
    
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    marker_points = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        perimeter = cv2.arcLength(cnt, True)
        if perimeter > 0:
            circularity = 4 * math.pi * area / (perimeter ** 2)
        else:
            circularity = 0
        
        # 过滤：面积适中 + 圆度高
        if 15 < area < 200 and circularity > 0.5:
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                r = math.sqrt(area / math.pi)
                marker_points.append({
                    "cx": float(cx), "cy": float(cy), 
                    "r": float(r), "area": float(area),
                    "circularity": float(circularity)
                })
    
    # --- 检测箭头方向（通过骨架化 + 端点分析）---
    edges = cv2.Canny(gray, 80, 200)
    # 只保留长线段
    lines_raw = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=30,
        minLineLength=15, maxLineGap=3
    )
    long_lines = []
    if lines_raw is not None:
        for l in lines_raw:
            x1, y1, x2, y2 = l[0]
            length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            if length > 20:
                angle = math.degrees(math.atan2(y2-y1, x2-x1))
                long_lines.append({
                    "x1": float(x1), "y1": float(y1),
                    "x2": float(x2), "y2": float(y2),
                    "length": float(length), "angle": float(angle)
                })
    
    return {
        "image_size": {"w": w, "h": h},
        "circles": [{"cx": c[0], "cy": c[1], "r": c[2]} for c in circles],
        "marker_points": marker_points,
        "long_lines": long_lines
    }

# ============================================================
# Step 3: 智能重建 — 基于分析结果构建精确 SVG
# ============================================================
def reconstruct_svg(geo: dict, ocr_texts: list) -> str:
    """
    基于几何分析 + OCR 结果，智能重建高质量 SVG。
    核心策略：用检测到的圆心聚类确定轨道组，而非逐线段拼接。
    """
    iw = geo["image_size"]["w"]
    ih = geo["image_size"]["h"]
    
    # 放大到试卷尺寸（2.5x）
    scale = 2.5
    margin = 30
    svg_w = int(iw * scale) + margin * 2
    svg_h = int(ih * scale) + margin * 2
    
    parts = []
    
    # SVG 头部
    parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{svg_w}" height="{svg_h}" 
     viewBox="0 0 {svg_w} {svg_h}"
     style="background: white;">
  <defs>
    <marker id="arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#C00"/>
    </marker>
    <style>
      .orbit {{ stroke: #000; fill: none; stroke-dasharray: 6,4; stroke-width: 1.5; }}
      .orbit-i {{ stroke: #C00; fill: none; stroke-width: 1.8; marker-end: url(#arr); }}
      .planet {{ fill: #fff; stroke: #000; stroke-width: 1.5; }}
      .planet-fill {{ fill: #F0F0F0; stroke: #000; stroke-width: 1.5; }}
      .label {{ font-size: 15px; font-family: {FONT_FAMILY}; fill: #000; }}
      .label-bold {{ font-size: 15px; font-family: {FONT_FAMILY}; fill: #000; font-weight: 700; }}
      .dot {{ fill: #000; }}
      .orbit-tag {{ font-size: 13px; font-family: {FONT_FAMILY}; fill: #000; font-style: italic; }}
    </style>
  </defs>
  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="white"/>''')
    
    def tx(x): return x * scale + margin
    def ty(y): return y * scale + margin
    
    # 分析圆形：找到中心圆（火星）和轨道圆
    circles = geo["circles"]
    
    # 按半径排序，最小的很可能是星球本体
    circles_sorted = sorted(enumerate(circles), key=lambda c: c[1]["r"])
    
    # 找到星球本体（最小的圆，且 OCR 检测到"火星"文字在其上）
    planet_idx = None
    planet_circle = None
    for ci, c in circles_sorted:
        # 检查是否有 OCR 文字在此圆内
        for t in ocr_texts:
            dist = math.sqrt((t["cx"] - c["cx"])**2 + (t["cy"] - c["cy"])**2)
            if dist < c["r"] + 10:
                planet_idx = ci
                planet_circle = c
                break
        if planet_idx is not None:
            break
    
    # 如果没找到星球，取最小圆
    if planet_idx is None and circles_sorted:
        planet_idx = circles_sorted[0][0]
        planet_circle = circles_sorted[0][1]
    
    # 绘制轨道（排除星球本体后的圆）
    parts.append('\n  <!-- 轨道 -->')
    orbit_count = 0
    for ci, c in enumerate(circles):
        if ci == planet_idx:
            continue
        r = c["r"]
        cx_s = tx(c["cx"])
        cy_s = ty(c["cy"])
        
        # 只保留半径合理的圆（排除噪声检测）
        if r < 25:
            continue
        
        orbit_count += 1
        orbit_label = ["I", "II", "III", "IV"][orbit_count - 1] if orbit_count <= 4 else str(orbit_count)
        
        parts.append(f'  <g data-type="orbit" data-label="{orbit_label}">')
        parts.append(f'    <circle cx="{cx_s:.1f}" cy="{cy_s:.1f}" r="{r * scale:.1f}" class="orbit"/>')
        # 轨道标签放在右上角
        parts.append(f'    <text x="{cx_s + r * scale * 0.7:.1f}" y="{cy_s - r * scale * 0.7:.1f}" class="orbit-tag">{orbit_label}</text>')
        parts.append(f'  </g>')
    
    # 绘制星球
    if planet_circle:
        pcx = tx(planet_circle["cx"])
        pcy = ty(planet_circle["cy"])
        pr = planet_circle["r"] * scale
        parts.append('\n  <!-- 火星 -->')
        parts.append(f'  <g data-type="planet">')
        parts.append(f'    <circle cx="{pcx:.1f}" cy="{pcy:.1f}" r="{pr:.1f}" class="planet-fill"/>')
        # OCR 识别到的"火星"标签
        parts.append(f'    <text x="{pcx:.1f}" y="{pcy + 5:.1f}" class="label-bold" text-anchor="middle">火星</text>')
        parts.append(f'  </g>')
    
    # 绘制标记点（S, Q, P）
    parts.append('\n  <!-- 标记点 -->')
    for pi, pt in enumerate(geo["marker_points"]):
        cx_s = tx(pt["cx"])
        cy_s = ty(pt["cy"])
        r_s = max(3, pt["r"] * scale * 0.6)
        
        # 默认标签（OCR 没识别到时用序号）
        default_labels = ["S", "Q", "P", "P₁", "P₂", "P₃"]
        label = default_labels[pi] if pi < len(default_labels) else f"P{pi}"
        
        # 查找最近的 OCR 文字
        for t in ocr_texts:
            dist = math.sqrt((t["cx"] - pt["cx"])**2 + (t["cy"] - pt["cy"])**2)
            if dist < 25:
                label = t["text"]
                break
        
        parts.append(f'  <g data-type="marker" data-label="{label}">')
        parts.append(f'    <circle cx="{cx_s:.1f}" cy="{cy_s:.1f}" r="{r_s:.1f}" class="dot"/>')
        parts.append(f'    <text x="{cx_s + r_s + 4:.1f}" y="{cy_s + 4:.1f}" class="label-bold">{label}</text>')
        parts.append(f'  </g>')
    
    # 绘制轨迹箭头（长线段）
    parts.append('\n  <!-- 轨迹曲线 -->')
    for li, line in enumerate(geo["long_lines"]):
        x1 = tx(line["x1"])
        y1 = ty(line["y1"])
        x2 = tx(line["x2"])
        y2 = ty(line["y2"])
        # 只画真正长的线段（排除轨道碎片）
        if line["length"] > 25:
            parts.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="orbit-i" data-type="trajectory"/>')
    
    # 附加 OCR 未关联的文字
    parts.append('\n  <!-- OCR 额外文字 -->')
    used_texts = set()
    # 已关联到星球的文字
    if planet_circle:
        for t in ocr_texts:
            dist = math.sqrt((t["cx"] - planet_circle["cx"])**2 + (t["cy"] - planet_circle["cy"])**2)
            if dist < planet_circle["r"] + 10:
                used_texts.add(id(t))
    # 已关联到标记点的文字
    for pt in geo["marker_points"]:
        for t in ocr_texts:
            dist = math.sqrt((t["cx"] - pt["cx"])**2 + (t["cy"] - pt["cy"])**2)
            if dist < 25:
                used_texts.add(id(t))
    
    for t in ocr_texts:
        if id(t) not in used_texts:
            cx_s = tx(t["cx"])
            cy_s = ty(t["cy"])
            parts.append(f'  <text x="{cx_s:.1f}" y="{cy_s:.1f}" class="label" data-ocr="{t["text"]}">{t["text"]}</text>')
    
    parts.append('\n</svg>')
    return '\n'.join(parts)

# ============================================================
# Step 4: 试卷预览 HTML
# ============================================================
def build_exam_html(svg_path: Path, geo: dict, ocr_texts: list) -> str:
    svg_content = svg_path.read_text(encoding='utf-8')
    
    exam_question = "如图，火星绕太阳做匀速圆周运动，火星与太阳的间距为r₁，火星的运行周期为T₁。某航天器绕火星做匀速圆周运动，航天器与火星的间距为r₂，航天器的运行周期为T₂。已知火星的质量为M，引力常量为G，则（　　）"
    exam_options = [
        "A. 火星的线速度大小为 2πr₁/T₁",
        "B. 航天器的线速度大小为 2πr₂/T₂", 
        "C. 火星的质量 M = 4π²r₁³/(GT₁²)",
        "D. 航天器的运行周期 T₂ = 2π√(r₂³/GM)"
    ]
    
    # 构建分析报告
    ocr_list_html = ""
    for t in ocr_texts:
        ocr_list_html += f'<li><code>{t["text"]}</code> (置信度 {t["confidence"]:.0%})</li>'
    
    circle_list_html = ""
    for i, c in enumerate(geo["circles"]):
        circle_list_html += f'<li>圆{i}: 中心({c["cx"]:.0f},{c["cy"]:.0f}) 半径={c["r"]:.0f}</li>'
    
    point_list_html = ""
    for i, p in enumerate(geo["marker_points"]):
        point_list_html += f'<li>点{i}: ({p["cx"]:.0f},{p["cy"]:.0f}) r={p["r"]:.1f}</li>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>物理试卷 SVG 嵌入预览</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700&family=Noto+Serif+SC:wght@400;700&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ 
    background: #e8e4df; font-family: 'Noto Serif SC', 'SimSun', serif;
    display: flex; flex-direction: column; align-items: center;
    padding: 30px 20px;
  }}
  .page {{
    background: white; width: 210mm; min-height: 297mm;
    padding: 25mm 30mm; box-shadow: 0 2px 20px rgba(0,0,0,0.15);
    margin-bottom: 30px; position: relative;
  }}
  .page::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 4px; background: #c00;
  }}
  .exam-header {{
    text-align: center; border-bottom: 2px solid #000;
    padding-bottom: 15px; margin-bottom: 25px;
  }}
  .exam-header h1 {{ font-size: 22px; font-weight: 700; letter-spacing: 8px; }}
  .exam-header p {{ font-size: 13px; color: #666; margin-top: 5px; }}
  .section-title {{
    font-size: 15px; font-weight: 700; margin: 20px 0 12px 0;
    border-left: 3px solid #c00; padding-left: 10px;
  }}
  .question {{ margin: 18px 0; font-size: 15px; line-height: 1.8; }}
  .question .q-num {{ font-weight: 700; }}
  .figure-container {{
    display: flex; justify-content: center; margin: 15px 0; padding: 10px;
  }}
  .figure-container svg {{ max-width: 320px; }}
  .options {{ margin: 8px 0 8px 24px; line-height: 2; }}
  
  .workflow-card {{
    background: white; width: 210mm; padding: 25mm 30mm;
    box-shadow: 0 2px 20px rgba(0,0,0,0.15);
  }}
  .workflow-card h2 {{ font-size: 18px; margin-bottom: 15px; color: #333; }}
  .workflow-card .step {{
    background: #f8f7f5; border-left: 4px solid #c00;
    padding: 12px 15px; margin: 10px 0; border-radius: 0 6px 6px 0;
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
    width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px;
  }}
  .method-compare th {{ background: #f0f0ec; padding: 8px 12px; text-align: left; }}
  .method-compare td {{ padding: 8px 12px; border-bottom: 1px solid #e0e0dc; }}
  .method-compare .recommended {{ background: #fffbe6; }}
  
  .analysis-box {{
    background: #f5f5f0; padding: 15px; border-radius: 8px;
    margin-top: 15px; font-size: 13px; line-height: 1.8;
  }}
  .analysis-box h4 {{ margin: 0 0 8px 0; font-size: 14px; }}
  .analysis-box ul {{ margin-left: 20px; }}
</style>
</head>
<body>

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
  
  <div style="margin-top: 30px; border-top: 1px solid #ccc; padding-top: 15px; font-size: 12px; color: #999; text-align: center;">
    ▲ SVG 直接嵌入试卷效果 — 所有文字为 &lt;text&gt; 元素，可直接选中编辑
  </div>
</div>

<div class="workflow-card">
  <h2>📐 SVG 在物理试卷中的工作流</h2>
  
  <div class="step">
    <span class="step-num">1</span>
    <b>编辑源文件</b>：用 Inkscape / Illustrator 打开 <code>.svg</code>，修改任何元素
  </div>
  
  <div class="step">
    <span class="step-num">2</span>
    <b>导出为试卷格式</b>：
    <table class="method-compare">
      <tr><th>试卷工具</th><th>嵌入方式</th><th>操作</th></tr>
      <tr class="recommended">
        <td><b>Word / WPS（主流）</b></td>
        <td>PNG (300dpi)</td>
        <td>Inkscape → 导出 PNG → 插入 Word</td>
      </tr>
      <tr>
        <td><b>LaTeX</b></td>
        <td>PDF</td>
        <td>Inkscape → 另存 PDF → \\includegraphics</td>
      </tr>
      <tr>
        <td><b>HTML 在线试卷</b></td>
        <td>SVG 直接嵌入</td>
        <td>&lt;img src="xxx.svg"&gt; 或内联</td>
      </tr>
    </table>
  </div>
  
  <div class="step">
    <span class="step-num">3</span>
    <b>核心原则</b>：<span class="highlight">SVG 是源码，PNG 是编译产物</span>。永远编辑 SVG，需要时导出 PNG。<br/>
    <span style="color:#666">❌ 不要 SVG→JPG→再转SVG，那会丢失所有可编辑性！</span>
  </div>
  
  <div class="analysis-box">
    <h4>📊 本次分析结果</h4>
    <p>图片尺寸: {geo['image_size']['w']}×{geo['image_size']['h']}px</p>
    <p>检测到 {len(geo['circles'])} 个圆形：</p>
    <ul>{circle_list_html}</ul>
    <p>检测到 {len(geo['marker_points'])} 个标记点：</p>
    <ul>{point_list_html}</ul>
    <p>OCR 识别到 {len(ocr_texts)} 个文字区域：</p>
    <ul>{ocr_list_html}</ul>
  </div>
</div>

</body>
</html>"""
    return html

# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("物理题图片 → 可编辑 SVG 转换器 v6")
    print("RapidOCR + OpenCV + 智能重建")
    print("=" * 60)
    
    # Step 1: OCR
    print("\n[1/4] OCR 文字识别 (RapidOCR)...")
    try:
        texts = run_ocr(INPUT_IMAGE)
        print(f"  识别到 {len(texts)} 个文字区域:")
        for t in texts:
            print(f"    '{t['text']}' (置信度: {t['confidence']:.1%}) @ ({t['cx']:.0f}, {t['cy']:.0f})")
    except Exception as e:
        print(f"  ⚠ OCR 失败: {e}")
        texts = []
    
    # Step 2: 几何分析
    print("\n[2/4] 图像几何分析...")
    geo = analyze_image_structure(INPUT_IMAGE)
    print(f"  图片: {geo['image_size']['w']}×{geo['image_size']['h']}")
    print(f"  圆形: {len(geo['circles'])} 个")
    for i, c in enumerate(geo["circles"]):
        print(f"    圆{i}: 中心({c['cx']:.0f},{c['cy']:.0f}) 半径={c['r']:.0f}")
    print(f"  标记点: {len(geo['marker_points'])} 个")
    for i, p in enumerate(geo["marker_points"]):
        print(f"    点{i}: ({p['cx']:.0f},{p['cy']:.0f}) r={p['r']:.1f} 圆度={p['circularity']:.2f}")
    print(f"  长线段: {len(geo['long_lines'])} 条")
    
    # Step 3: SVG 重建
    print("\n[3/4] 智能重建 SVG...")
    svg = reconstruct_svg(geo, texts)
    OUTPUT_SVG.write_text(svg, encoding='utf-8')
    print(f"  ✅ SVG: {OUTPUT_SVG}")
    
    # 保存分析数据
    analysis = {
        "version": "v6",
        "image_size": geo["image_size"],
        "ocr_texts": [{"text": t["text"], "cx": t["cx"], "cy": t["cy"], "conf": t["confidence"]} for t in texts],
        "circles": geo["circles"],
        "marker_points": [{"cx": p["cx"], "cy": p["cy"], "r": p["r"]} for p in geo["marker_points"]],
        "long_lines_count": len(geo["long_lines"])
    }
    OUTPUT_ANALYSIS.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  ✅ 分析: {OUTPUT_ANALYSIS}")
    
    # Step 4: HTML 预览
    print("\n[4/4] 生成试卷预览页...")
    html = build_exam_html(OUTPUT_SVG, geo, texts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"  ✅ 预览: {OUTPUT_HTML}")
    
    print("\n" + "=" * 60)
    print("🎉 完成！打开 exam_preview_v5.html 查看效果")
    print("=" * 60)

if __name__ == "__main__":
    main()
