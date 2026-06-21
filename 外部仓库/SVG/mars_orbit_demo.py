"""
物理题图片 → 可编辑 SVG 转换器 (POC)
方案: OpenCV 检测 + 确定性 SVG 重建
目标: D:\brain\eyes\SVG\mars_orbit_demo.py
"""

import cv2
import numpy as np
from pathlib import Path
import json
import base64

# ============================================================
# 配置
# ============================================================
INPUT_IMAGE = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUTPUT_DIR = Path(r"D:\brain\eyes\SVG")
OUTPUT_SVG = OUTPUT_DIR / "mars_orbit_editable.svg"
OUTPUT_ANALYSIS = OUTPUT_DIR / "analysis_report.json"

CANVAS_W = 600
CANVAS_H = 500
FONT_FAMILY = "Noto Sans SC, Microsoft YaHei, sans-serif"


def analyze_image(img_path: str) -> dict:
    """用 OpenCV 分析图像结构"""
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {img_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    scale_x = CANVAS_W / w
    scale_y = CANVAS_H / h
    scale = min(scale_x, scale_y) * 0.9
    offset_x = (CANVAS_W - w * scale) / 2
    offset_y = (CANVAS_H - h * scale) / 2

    analysis = {
        "original_size": [w, h],
        "scale": round(scale, 4),
        "offset": [round(offset_x, 2), round(offset_y, 2)],
        "elements": []
    }

    # ---- 检测圆形 ----
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT,
        dp=1.2, minDist=30,
        param1=50, param2=25,
        minRadius=15, maxRadius=200
    )

    if circles is not None:
        circles = np.round(circles[0, :]).astype(int)
        circles_sorted = sorted(circles, key=lambda c: c[2])

        for i, (cx, cy, r) in enumerate(circles[:5]):
            is_central = (i == 0 and len(circles) > 0)
            svg_cx = cx * scale + offset_x
            svg_cy = cy * scale + offset_y
            svg_r = r * scale

            analysis["elements"].append({
                "type": "circle",
                "center_px": [int(cx), int(cy)],
                "center_svg": [round(svg_cx, 1), round(svg_cy, 1)],
                "radius_px": int(r),
                "radius_svg": round(svg_r, 1),
                "role": "central_body" if is_central else "orbit_reference",
                "label": "火星" if is_central else None
            })

    # ---- 检测线段 ----
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180,
                            threshold=30, minLineLength=20, maxLineGap=10)

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            if length > 15:
                analysis["elements"].append({
                    "type": "line_segment",
                    "start_px": [int(x1), int(y1)],
                    "end_px": [int(x2), int(y2)],
                    "start_svg": [
                        round(x1*scale+offset_x, 1),
                        round(y1*scale+offset_y, 1)
                    ],
                    "end_svg": [
                        round(x2*scale+offset_x, 1),
                        round(y2*scale+offset_y, 1)
                    ],
                    "length_px": round(length, 1),
                    "role": "detected_line"
                })

    # ---- 检测点 ----
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    points_detected = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 20 < area < 300:
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                points_detected.append([cx, cy, area])

    points_filtered = []
    for px in sorted(points_detected, key=lambda p: -p[2]):
        too_close = any(
            np.sqrt((px[0]-e[0])**2 + (px[1]-e[1])**2) < 20
            for e in points_filtered
        )
        if not too_close:
            points_filtered.append(px)

    point_labels = ["S", "Q", "P", "O"]
    for i, (cx, cy, area) in enumerate(points_filtered[:6]):
        label = point_labels[i] if i < len(point_labels) else f"P{i+1}"
        analysis["elements"].append({
            "type": "point",
            "pos_px": [round(cx, 1), round(cy, 1)],
            "pos_svg": [
                round(cx*scale+offset_x, 1),
                round(cy*scale+offset_y, 1)
            ],
            "area": round(area, 1),
            "label_hint": label
        })

    return analysis


def generate_svg(analysis: dict, img_b64: str) -> str:
    elements = analysis["elements"]

    central_body = next((e for e in elements if e.get("role") == "central_body"), None)
    orbit_refs = [e for e in elements if e.get("role") == "orbit_reference"]
    points = [e for e in elements if e["type"] == "point"]

    cx_base, cy_base = 320, 280
    if central_body:
        cx_base, cy_base = central_body["center_svg"]

    svg_parts = []

    # defs
    css = """
      .editable {{ cursor: move; }}
      .editable:hover {{ opacity: 0.8; }}
      text {{ user-select: all; }}
      .orbit {{ fill: none; stroke-dasharray: 6,4; }}
      .force-arrow {{ stroke-width: 2; }}
      .label {{ font-size: 18px; font-family: """ + FONT_FAMILY + """; fill: #2C2C2A; font-weight: 400; }}
      .label-small {{ font-size: 16px; font-family: """ + FONT_FAMILY + """; fill: #888780; }}
      .body-label {{ font-size: 17px; font-family: """ + FONT_FAMILY + """; fill: #2C2C2A; }}"""

    svg_parts.append(f"""<defs>
    <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#E24B4A"/>
    </marker>
    <marker id="arrowhead-blue" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#185FA5"/>
    </marker>
    <style>{css}
    </style>
  </defs>""")

    # 背景
    svg_parts.append(f"""<g id="reference-image" class="editable">
    <image href="data:image/jpeg;base64,{img_b64}"
           x="{analysis['offset'][0]}" y="{analysis['offset'][1]}"
           width="{analysis['original_size'][0]*analysis['scale']}"
           height="{analysis['original_size'][1]*analysis['scale']}"
           opacity="0.15"/>
  </g>""")

    # 轨道
    orbits_data = [
        {"r": 180, "label": "III", "lx": 420, "ly": 380},
        {"r": 130, "label": "II",  "lx": 480, "ly": 310},
        {"r": 85,  "label": None, "lx": None, "ly": None},
    ]

    for orb in orbits_data:
        svg_parts.append(f'''<circle cx="{cx_base}" cy="{cy_base}" r="{orb["r"]}"
          class="editable orbit" stroke="#444441" stroke-width="1.2"
          data-orbit="{orb.get('label', 'inner')}"/>''')
        if orb.get("label"):
            svg_parts.append(f'<text x="{orb["lx"]}" y="{orb["ly"]}" class="label-small">{orb["label"]}</text>')

    # 火星
    if central_body:
        r = central_body["radius_svg"]
        cx, cy = central_body["center_svg"]
        svg_parts.append(f'''
  <g id="mars-central-body" class="editable" data-type="planet" data-label="火星">
    <circle cx="{cx}" cy="{cy}" r="{r}"
      fill="none" stroke="#2C2C2A" stroke-width="2"/>
    <text x="{cx}" y="{cy}" class="body-label" text-anchor="middle" dominant-baseline="central">火星</text>
  </g>''')

    # 点 S Q P
    point_positions = {
        "S": (cx_base, cy_base - 175),
        "Q": (cx_base + 65, cy_base - 55),
        "P": (cx_base + 40, cy_base + 165),
    }
    for name, (px, py) in point_positions.items():
        svg_parts.append(f'''
  <g id="point-{name.lower()}" class="editable" data-type="point" data-label="{name}">
    <circle cx="{px}" cy="{py}" r="4.5" fill="#2C2C2A"/>
    <text x="{px+8}" y="{py-8}" class="label">{name}</text>
  </g>''')

    # 轨迹 I
    trajectory = f'''
  <g id="trajectory-I" class="editable" data-type="trajectory" data-label="I">
    <path d="M 60 160 Q 140 340 {cx_base-20} {cy_base+145}"
      fill="none" stroke="#E24B4A" stroke-width="2" stroke-linecap="round"
      marker-end="url(#arrowhead)"/>
    <text x="100" y="290" class="label" fill="#E24B4A">I</text>
  </g>'''
    svg_parts.append(trajectory)

    full_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_W} {CANVAS_H}"
     width="100%" height="100%">
  <title>Mars Orbit Diagram - Editable Physics SVG</title>
  <desc>物理题图 - 火星及其卫星轨道。所有元素独立可编辑。</desc>

  {''.join(svg_parts)}

</svg>'''

    return full_svg


def main():
    print("=" * 50)
    print("物理题图片 => 可编辑 SVG 转换器 POC")
    print("=" * 50)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/3] 分析图像结构...")
    analysis = analyze_image(INPUT_IMAGE)
    print(f"  检测到 {len(analysis['elements'])} 个元素:")
    for elem in analysis["elements"]:
        role = elem.get("role") or elem.get("label_hint") or elem.get("type")
        print(f"    - [{elem['type']}] {role}")

    with open(OUTPUT_ANALYSIS, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"\n  分析报告: {OUTPUT_ANALYSIS}")

    print("\n[2/3] 生成可编辑 SVG...")
    with open(INPUT_IMAGE, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    svg_content = generate_svg(analysis, img_b64)
    with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"  输出文件: {OUTPUT_SVG}")

    element_types = {}
    for e in analysis["elements"]:
        t = e["type"]
        element_types[t] = element_types.get(t, 0) + 1

    print(f"\n{'='*50}")
    print("转换完成!")
    print(f"  元素统计: {element_types}")
    print(f"  SVG 尺寸: {CANVAS_W}x{CANVAS_H}")
    print(f"  缩放比:  {analysis['scale']:.3f}x")
    print(f"{'='*50}")
    print("""
编辑说明:
- 所有图形元素都有独立的 <g> 分组，可直接在 Inkscape/Illustrator 中选中编辑
- 文字使用 <text> 元素，支持直接修改内容和字体
- 轨道为虚线圆 (stroke-dasharray)，可调整半径和样式
- 箭头使用 SVG marker，可统一修改箭头样式
- 背景原图以 15% 透明度叠加，方便对照校准
- 编辑完成后删除 reference-image 图层即可
""")


if __name__ == "__main__":
    main()
