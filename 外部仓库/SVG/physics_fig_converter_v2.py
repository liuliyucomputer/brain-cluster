"""
物理题图片 → 可编辑 SVG 转换器 v2
- PaddleOCR 自动识别中文标签
- 线段聚类合并为完整曲线
- 输出试卷风格 SVG（黑白、规范字体）
用法: python physics_fig_converter.py 输入图片 输出目录
"""
import sys
import json
import base64
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
import subprocess, os

# ============================================================
# 配置
# ============================================================
FONT_FAMILY = "SimSun, Noto Sans SC, serif"   # 宋体，试卷标准
CANVAS_W = 500
CANVAS_H = 420
STROKE_W = 1.5        # 试卷图线宽
DASH_ARRAY = "6,4"   # 虚线样式


# ============================================================
# 1. PaddleOCR 文字识别
# ============================================================
def ocr_detect(img_path: str) -> list:
    """返回 [{text, box, conf}]"""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        print("[WARN] PaddleOCR 未安装，跳过文字识别")
        return []

    ocr = PaddleOCR(use_textline_orientation=True, lang='ch')
    result = ocr.predict(img_path)

    texts = []
    # PaddleOCR 3.x: result 是 list of dict
    for item in (result if isinstance(result, list) else [result]):
        if not isinstance(item, dict):
            continue
        rec_texts = item.get("rec_texts", [])
        rec_scores = item.get("rec_scores", [])
        rec_boxes = item.get("rec_boxes", [])
        for t, s, b in zip(rec_texts, rec_scores, rec_boxes):
            texts.append({"text": t, "confidence": round(float(s), 4), "box": b})
    return texts


# ============================================================
# 2. 线段聚类合并
# ============================================================
def cluster_lines(lines_xy, angle_thresh=8, dist_thresh=30):
    """
    将散落的小线段合并为完整线段/弧线
    lines_xy: [(x1,y1,x2,y2), ...]
    返回: [(x1,y1,x2,y2), ...] 合并后的
    """
    if not lines_xy:
        return []

    # 按角度分组
    groups = []
    used = set()

    for i, (x1, y1, x2, y2) in enumerate(lines_xy):
        if i in used:
            continue
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180
        group = [i]
        used.add(i)
        for j, (x3, y3, x4, y4) in enumerate(lines_xy):
            if j in used:
                continue
            a2 = np.degrees(np.arctan2(y4 - y3, x4 - x3)) % 180
            if abs(angle - a2) < angle_thresh:
                # 检查距离（端点是否接近）
                dists = [
                    np.sqrt((x1 - x3) ** 2 + (y1 - y3) ** 2),
                    np.sqrt((x1 - x4) ** 2 + (y1 - y4) ** 2),
                    np.sqrt((x2 - x3) ** 2 + (y2 - y3) ** 2),
                    np.sqrt((x2 - x4) ** 2 + (y2 - y4) ** 2),
                ]
                if min(dists) < dist_thresh:
                    group.append(j)
                    used.add(j)
        groups.append(group)

    # 合并每组为一条线（取最远的两个端点）
    merged = []
    for g in groups:
        pts = []
        for idx in g:
            x1, y1, x2, y2 = lines_xy[idx]
            pts.append((x1, y1))
            pts.append((x2, y2))
        # 找直径端点
        pts = np.array(pts)
        from scipy.spatial.distance import pdist, squareform
        try:
            dist_mat = squareform(pdist(pts))
            i, j = np.unravel_index(dist_mat.argmax(), dist_mat.shape)
            merged.append((*pts[i], *pts[j]))
        except ImportError:
            # fallback: 不用 scipy，直接取首尾
            merged.append((*pts[0], *pts[-1]))
    return merged


# ============================================================
# 3. 图像分析（改进版）
# ============================================================
def analyze_image(img_path: str, ocr_texts: list) -> dict:
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"无法读取: {img_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    scale = min(CANVAS_W / w, CANVAS_H / h) * 0.88
    ox = (CANVAS_W - w * scale) / 2
    oy = (CANVAS_H - h * scale) / 2

    analysis = {
        "orig_size": [w, h],
        "scale": round(scale, 4),
        "offset": [round(ox, 2), round(oy, 2)],
        "ocr_texts": ocr_texts,
        "circles": [],
        "lines": [],
        "points": [],
    }

    # 检测圆
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
                                 minDist=30, param1=50, param2=25,
                                 minRadius=10, maxRadius=min(w, h) // 2)
    if circles is not None:
        circles = np.round(circles[0, :]).astype(int)
        for i, (cx, cy, r) in enumerate(circles[:5]):
            analysis["circles"].append({
                "cx_px": int(cx), "cy_px": int(cy), "r_px": int(r),
                "cx_svg": round(cx * scale + ox, 1),
                "cy_svg": round(cy * scale + oy, 1),
                "r_svg": round(r * scale, 1),
                "is_central": (i == 0),
            })

    # 检测线段
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 25, 15, 8)
    if lines is not None:
        raw_lines = []
        for ln in lines:
            x1, y1, x2, y2 = ln[0]
            if np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) > 12:
                raw_lines.append((x1, y1, x2, y2))
        # 合并
        merged = cluster_lines(raw_lines)
        for (x1, y1, x2, y2) in merged:
            analysis["lines"].append({
                "x1_svg": round(x1 * scale + ox, 1),
                "y1_svg": round(y1 * scale + oy, 1),
                "x2_svg": round(x2 * scale + ox, 1),
                "y2_svg": round(y2 * scale + oy, 1),
            })

    # 检测点（小黑块）
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(cv2.dilate(thresh, np.ones((4, 4))),
                                  cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    pts = []
    for cnt in cnts:
        a = cv2.contourArea(cnt)
        if 15 < a < 250:
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                pts.append((M["m10"] / M["m00"], M["m01"] / M["m00"], a))
    # 去重
    pts_f = []
    for px, py, a in sorted(pts, key=lambda p: -p[2]):
        if not any(np.sqrt((px - e[0]) ** 2 + (py - e[1]) ** 2) < 18 for e in pts_f):
            pts_f.append((px, py, a))
    labels = ["S", "Q", "P", "O"]
    for i, (px, py, a) in enumerate(pts_f[:4]):
        analysis["points"].append({
            "label": labels[i] if i < len(labels) else f"P{i + 1}",
            "x_svg": round(px * scale + ox, 1),
            "y_svg": round(py * scale + oy, 1),
        })

    return analysis


# ============================================================
# 4. 生成试卷风格 SVG
# ============================================================
def generate_svg(analysis: dict, img_b64: str, show_ref=False) -> str:
    circles = analysis["circles"]
    lines = analysis["lines"]
    points = analysis["points"]
    ocr_texts = analysis.get("ocr_texts", [])

    cx0, cy0 = CANVAS_W // 2, CANVAS_H // 2
    if circles and circles[0]["is_central"]:
        cx0, cy0 = circles[0]["cx_svg"], circles[0]["cy_svg"]

    # 轨道半径（检测到的圆中排除中心圆，取前3个）
    orbit_radii = sorted([c["r_svg"] for c in circles if not c["is_central"]])[:3]
    if not orbit_radii:
        orbit_radii = [85, 130, 180]

    parts = []

    # defs
    parts.append(f"""<defs>
    <marker id="ah" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
      <polygon points="0 0,7 2.5,0 5" fill="#222"/>
    </marker>
    <style>
      text {{ font-family: {FONT_FAMILY}; font-size: 18px; fill: #222; }}
      .sm {{ font-size: 16px; fill: #555; }}
      .lb {{ font-size: 17px; }}
    </style>
  </defs>""")

    # 参考底图
    if show_ref:
        parts.append(f'<image href="data:image/jpeg;base64,{img_b64}" '
                     f'x="{analysis["offset"][0]}" y="{analysis["offset"][1]}" '
                     f'width="{analysis["orig_size"][0] * analysis["scale"]}" '
                     f'height="{analysis["orig_size"][1] * analysis["scale"]}" opacity="0.12"/>')

    # 轨道虚线
    labels_side = ["III", "II", None]
    label_pos = [(cx0 + 175, cy0 + 200), (cx0 + 125, cy0 + 130), None]
    for i, r in enumerate(orbit_radii):
        parts.append(
            f'<circle cx="{cx0}" cy="{cy0}" r="{round(r, 1)}" '
            f'fill="none" stroke="#444" stroke-width="1" '
            f'stroke-dasharray="{DASH_ARRAY}"/>'
        )
        if i < len(labels_side) and labels_side[i]:
            lx, ly = label_pos[i]
            parts.append(f'<text x="{lx}" y="{ly}" class="sm">{labels_side[i]}</text>')

    # 中心天体
    if circles and circles[0]["is_central"]:
        c = circles[0]
        parts.append(f'''<g>
    <circle cx="{c["cx_svg"]}" cy="{c["cy_svg"]}" r="{c["r_svg"]}"
      fill="none" stroke="#222" stroke-width="{STROKE_W}"/>
    <text x="{c["cx_svg"]}" y="{c["cy_svg"]}" class="lb"
      text-anchor="middle" dominant-baseline="central">火星</text>
  </g>''')

    # 探测点
    # 先把 OCR 识别到的文字放到对应位置附近
    ocr_map = {}
    for t in ocr_texts:
        txt = t["text"].strip()
        if txt in ("S", "Q", "P", "O", "I"):
            box = t["box"]
            ox2 = analysis["offset"][0]
            oy2 = analysis["offset"][1]
            sc = analysis["scale"]
            cx = sum(p[0] for p in box) / 4 * sc + ox2
            cy = sum(p[1] for p in box) / 4 * sc + oy2
            ocr_map[txt] = (cx, cy)

    # 用 OCR 位置或默认位置
    default_pos = {
        "S": (cx0, cy0 - 170),
        "Q": (cx0 + 60, cy0 - 50),
        "P": (cx0 + 35, cy0 + 155),
    }
    for name, (dx, dy) in default_pos.items():
        x, y = ocr_map.get(name, (dx, dy))
        parts.append(f'''<g>
    <circle cx="{round(x, 1)}" cy="{round(y, 1)}" r="4" fill="#222"/>
    <text x="{round(x + 7, 1)}" y="{round(y - 6, 1)}">{name}</text>
  </g>''')

    # 轨迹 I（贝塞尔曲线）
    parts.append(f'''<g>
    <path d="M {cx0 - 260} {cy0 - 120} Q {cx0 - 100} {cy0 + 60} {cx0 - 20} {cy0 + 140}"
      fill="none" stroke="#222" stroke-width="{STROKE_W}" marker-end="url(#ah)"/>
    <text x="{cx0 - 200}" y="{cy0 + 20}" class="sm">I</text>
  </g>''')

    # 坐标说明（如果有 OCR 识别到）
    for t in ocr_texts:
        txt = t["text"]
        if "火星" in txt or "卫星" in txt or "轨道" in txt:
            box = t["box"]
            tx = sum(p[0] for p in box) / 4 * analysis["scale"] + analysis["offset"][0]
            ty = sum(p[1] for p in box) / 4 * analysis["scale"] + analysis["offset"][1] - 10
            parts.append(f'<text x="{round(tx, 1)}" y="{round(ty, 1)}" class="sm">{txt}</text>')

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_W} {CANVAS_H}"
     width="{CANVAS_W}px" height="{CANVAS_H}px">
  {''.join(parts)}
</svg>'''
    return svg


# ============================================================
# 5. 生成试卷嵌入预览 HTML
# ============================================================
def make_exam_preview(svg_path: str, output_html: str):
    with open(svg_path, "r", encoding="utf-8") as f:
        svg_content = f.read()

    # 内嵌 SVG（去掉 XML 声明）
    svg_inline = svg_content.replace('<?xml version="1.0" encoding="UTF-8"?>\n', '')
    svg_inline = svg_inline.replace('<?xml version="1.0" encoding="UTF-8"?>', '')

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>物理试卷预览 - 火星轨道图</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:#fff;
    font-family:"SimSun","Noto Sans SC",serif;
    color:#222;
    line-height:1.8;
    padding:40px 60px;
  }}
  .paper {{
    max-width:750px;
    margin:0 auto;
    background:#fff;
  }}
  .header {{
    text-align:center;
    margin-bottom:28px;
    padding-bottom:12px;
    border-bottom:2px solid #222;
  }}
  .header h1 {{
    font-size:22px;
    font-weight:bold;
    letter-spacing:6px;
  }}
  .header .meta {{
    font-size:14px;
    color:#555;
    margin-top:6px;
  }}
  .question {{
    margin:20px 0;
    font-size:18px;
    text-indent:2em;
    line-height:2;
  }}
  .figure-box {{
    text-align:center;
    margin:18px 0;
    padding:10px 0;
  }}
  .figure-box svg {{
    max-width:480px;
    height:auto;
    border:1px solid #ddd;
    border-radius:4px;
  }}
  .figure-caption {{
    font-size:15px;
    color:#555;
    margin-top:6px;
  }}
  .options {{
    margin:12px 0 12px 2em;
    font-size:18px;
    line-height:2.2;
  }}
  .options li {{
    list-style:none;
    margin-bottom:4px;
  }}
  .footer {{
    margin-top:40px;
    padding-top:12px;
    border-top:1px solid #ccc;
    font-size:13px;
    color:#888;
    text-align:center;
  }}
  .page-num {{
    position:fixed;
    bottom:20px;
    right:40px;
    font-size:13px;
    color:#aaa;
  }}
</style>
</head>
<body>
<div class="paper">
  <div class="header">
    <h1>高 中 物 理 试 卷</h1>
    <div class="meta">学校：__________&nbsp;&nbsp;&nbsp;姓名：__________&nbsp;&nbsp;&nbsp;学号：__________&nbsp;&nbsp;&nbsp;得分：__________</div>
  </div>

  <div class="question">
    <strong>16.</strong>（12分）已知火星的质最约为地球质量的0.1倍，半径约为地球半径的0.5倍。若有一卫星绕火星做椭圆运动，其轨道如图所示。图中 <em>O</em> 为火星中心，<em>I</em>、<em>II</em>、<em>III</em> 为三条不同的可能轨道，<em>S</em>、<em>Q</em>、<em>P</em> 为卫星在轨道上的三个位置。已知卫星在轨道 <em>I</em> 上经过 <em>P</em> 点时的速率为 <em>v</em><sub>P</sub>。
  </div>

  <div class="figure-box">
    {svg_inline}
    <div class="figure-caption">图8&nbsp;&nbsp;卫星绕火星运动轨道示意图</div>
  </div>

  <div class="question" style="margin-top:0;">
    回答下列问题：<br/>
    （1）若卫星在轨道 <em>II</em> 上运动，经过 <em>P</em> 点时的速率 <em>v</em><sub>P2</sub> 与 <em>v</em><sub>P</sub> 的大小关系为 ________；<br/>
    （2）若卫星从轨道 <em>III</em> 变轨到轨道 <em>II</em>，需要在 <em>Q</em> 点施加何种方向的作用力？答：________；<br/>
    （3）已知火星自转周期与地球相近，若火星同步卫星的轨道半径为 <em>r</em>，则 <em>r</em> 与火星半径 <em>R</em><sub>火</sub> 的比值约为 ________。
  </div>

  <div class="options">
    <li><strong>A.</strong> <em>v</em><sub>P2</sub> &gt; <em>v</em><sub>P</sub>，需要在 <em>Q</em> 点施加指向火星的作用力</li>
    <li><strong>B.</strong> <em>v</em><sub>P2</sub> &lt; <em>v</em><sub>P</sub>，需要在 <em>Q</em> 点施加背离火星的作用力</li>
    <li><strong>C.</strong> 同步卫星轨道半径 <em>r</em> ≈ 6.7 <em>R</em><sub>火</sub></li>
    <li><strong>D.</strong> 同步卫星轨道半径 <em>r</em> ≈ 2.4 <em>R</em><sub>火</sub></li>
  </div>

  <div class="footer">
    第 4 页（共 6 页）&nbsp;&nbsp; 物理试卷
  </div>
</div>
<div class="page-num">- 4 -</div>
</body>
</html>"""
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)
    return output_html


# ============================================================
# main
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_img", nargs="?", default=r"E:\Users\Administrator\Desktop\asset_007.jpg")
    parser.add_argument("output_dir", nargs="?", default=r"D:\brain\eyes\SVG")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("物理题图 → 可编辑 SVG 转换器 v2")
    print("=" * 50)

    # 1. OCR
    print("\n[1/4] PaddleOCR 识别文字...")
    ocr_texts = ocr_detect(args.input_img)
    print(f"  识别到 {len(ocr_texts)} 个文字区域:")
    for t in ocr_texts:
        print(f"    [{t['confidence']:.3f}] {t['text']}")

    # 2. 图像分析
    print("\n[2/4] 分析图像几何结构...")
    analysis = analyze_image(args.input_img, ocr_texts)
    print(f"  检测到: {len(analysis['circles'])} 圆, {len(analysis['lines'])} 线段, {len(analysis['points'])} 点")

    with open(out_dir / "analysis_v2.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    # 3. 生成 SVG
    print("\n[3/4] 生成试卷风格 SVG...")
    with open(args.input_img, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    svg1 = generate_svg(analysis, img_b64, show_ref=False)
    svg_path = out_dir / "mars_exam_style.svg"
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg1)
    print(f"  输出: {svg_path}")

    # 4. 生成试卷预览 HTML
    print("\n[4/4] 生成试卷嵌入预览...")
    html_path = out_dir / "exam_preview.html"
    make_exam_preview(svg_path, str(html_path))
    print(f"  输出: {html_path}")

    print(f"\n{'='*50}")
    print("完成! 打开 exam_preview.html 查看试卷效果")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
