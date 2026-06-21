"""
物理题图片 → 可编辑 SVG 转换器 v3
- 跳过 PaddleOCR（待修复 paddlepaddle 版本兼容性）
- 直接生成试卷级质量 SVG
- 输出 HTML 预览（嵌入模拟试卷版面）
用法: python physics_fig_converter_v3.py
"""

import base64, json, cv2, numpy as np
from pathlib import Path

# ============================================================
# 配置
# ============================================================
INPUT_IMG = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUTPUT_DIR = Path(r"D:\brain\eyes\SVG")
CANVAS_W = 480
CANVAS_H = 400
FONT_FAMILY = "SimSun, Noto Sans SC, sarif"
STROKE_W = 1.6

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. 图像分析（OpenCV 几何检测）
# ============================================================
def analyze_image(img_path: str) -> dict:
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"无法读取: {img_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    scale = min(CANVAS_W / w, CANVAS_H / h) * 0.85
    ox = (CANVAS_W - w * scale) / 2
    oy = (CANVAS_H - h * scale) / 2

    result = {
        "orig": [w, h],
        "scale": round(scale, 4),
        "offset": [round(ox, 2), round(oy, 2)],
    }

    # 检测圆（火星 + 轨道）
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2,
        minDist=30, param1=50, param2=25,
        minRadius=10, maxRadius=min(w, h) // 2
    )
    orbits = []
    mars = None
    if circles is not None:
        circles = np.round(circles[0, :]).astype(int)
        # 按半径排序，最小的是火星
        sorted_c = sorted([(c[0], c[1], c[2]) for c in circles], key=lambda x: x[2])
        if len(sorted_c) > 0:
            mx, my, mr = sorted_c[0]
            mars = {
                "cx": round(mx * scale + ox, 1),
                "cy": round(my * scale + oy, 1),
                "r":  round(mr * scale, 1),
            }
        # 其余当轨道
        for i, (cx, cy, cr) in enumerate(sorted_c[1:4]):
            orbits.append(round(cr * scale, 1))
        # 如果没有检测到足够的圆，用默认值
        if not orbits:
            orbits = [75, 120, 168]
    else:
        orbits = [75, 120, 168]

    result["mars"] = mars or {"cx": CANVAS_W // 2, "cy": CANVAS_H // 2, "r": 38}
    result["orbits"] = orbits[:3]
    return result


# ============================================================
# 2. 生成试卷风格 SVG
# ============================================================
def build_svg(analysis: dict) -> str:
    M = analysis["mars"]
    orbits = analysis["orbits"]

    # 探测点位置（根据图像比例估算）
    points = {
        "S": (M["cx"], M["cy"] - orbits[2] + 10),
        "Q": (M["cx"] + orbits[1] * 0.5, M["cy"] - orbits[1] * 0.35),
        "P": (M["cx"] + orbits[2] * 0.07, M["cy"] + orbits[2] - 5),
    }

    # 轨迹 I 的控制点
    traj = {
        "start": (M["cx"] - 220, M["cy"] - 90),
        "cp":     (M["cx"] - 80,  M["cy"] + 50),
        "end":   (M["cx"] + 10,   M["cy"] + orbits[2] - 8),
    }

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {CANVAS_W} {CANVAS_H}"
     width="{CANVAS_W}px" height="{CANVAS_H}px">
  <!-- 试卷物理图：火星轨道与卫星运动 -->
  <defs>
    <marker id="ah" markerWidth="7" markerHeight="5"
              refX="6" refY="2.5" orient="auto-start-reverse">
      <polygon points="0 0,7 2.5,0 5" fill="#222" stroke="none"/>
    </marker>
    <style>
      text {{ font-family: {FONT_FAMILY}; fill: #222; }}
      .fig {{ font-size: 17px; }}
      .sm  {{ font-size: 14px; fill: #444; }}
      .orbit {{ fill: none; stroke: #444; stroke-width: 1.1;
                stroke-dasharray: 5,3; }}
      .solid {{ fill: none; stroke: #222; stroke-width: {STROKE_W}; }}
    </style>
  </defs>

  <!-- 轨道 I, II, III（虚线圆）-->
  <circle cx="{{M['cx']}}" cy="{{M['cy']}}" r="{{orbits[2]}}"
          class="orbit"/>
  <circle cx="{{M['cx']}}" cy="{{M['cy']}}" r="{{orbits[1]}}"
          class="orbit"/>
  <circle cx="{{M['cx']}}" cy="{{M['cy']}}" r="{{orbits[0]}}"
          class="orbit"/>
  <!-- 轨道标签 -->
  <text x="{{M['cx'] + orbits[2] - 20}}" y="{{M['cy'] + orbits[2] + 18}}"
        class="sm">III</text>
  <text x="{{M['cx'] + orbits[1] + 10}}" y="{{M['cy'] - orbits[1] + 30}}"
        class="sm">II</text>

  <!-- 火星（中心天体）-->
  <g id="mars">
    <circle cx="{{M['cx']}}" cy="{{M['cy']}}" r="{{M['r']}}"
            fill="none" stroke="#222" stroke-width="{STROKE_W}"/>
    <text x="{{M['cx']}}" y="{{M['cy']}}"
          class="fig" text-anchor="middle" dominant-baseline="central">火星</text>
  </g>

  <!-- 探测点 S, Q, P -->
  <g id="point-S">
    <circle cx="{{points['S'][0]}}" cy="{{points['S'][1]}}" r="3.8" fill="#222"/>
    <text x="{{points['S'][0]+8}}" y="{{points['S'][1]-5}}"
          class="fig">S</text>
  </g>
  <g id="point-Q">
    <circle cx="{{points['Q'][0]}}" cy="{{points['Q'][1]}}" r="3.8" fill="#222"/>
    <text x="{{points['Q'][0]+8}}" y="{{points['Q'][1]-5}}"
          class="fig">Q</text>
  </g>
  <g id="point-P">
    <circle cx="{{points['P'][0]}}" cy="{{points['P'][1]}}" r="3.8" fill="#222"/>
    <text x="{{points['P'][0]+8}}" y="{{points['P'][1]-5}}"
          class="fig">P</text>
  </g>

  <!-- 轨迹 I（椭圆弧线 + 箭头）-->
  <path d="M {{traj['start'][0]}} {{traj['start'][1]}}
           Q {{traj['cp'][0]}} {{traj['cp'][1]}},
             {{traj['end'][0]}} {{traj['end'][1]}}"
        class="solid" marker-end="url(#ah)"/>
  <text x="{{(traj['start'][0] + traj['cp'][0]) // 2 - 10}}"
        y="{{(traj['start'][1] + traj['cp'][1]) // 2}}"
        class="sm">I</text>

  <!-- 参考圆点 O（火星中心）-->
  <g id="point-O">
    <circle cx="{{M['cx']}}" cy="{{M['cy'] - M['r'] - 6}}" r="2.5" fill="#666"/>
    <text x="{{M['cx'] + 8}}" y="{{M['cy'] - M['r'] - 2}}"
          class="sm" fill="#666">O</text>
  </g>

</svg>'''

    # 替换模板变量
    svg = svg.replace("{{M['cx']}}", str(M["cx"]))
    svg = svg.replace("{{M['cy']}}", str(M["cy"]))
    svg = svg.replace("{{M['r']}}", str(M["r"]))
    for i, r in enumerate(orbits):
        svg = svg.replace(f"{{{{orbits[{i}]}}}}", str(r))
    for name, (px, py) in points.items():
        svg = svg.replace(f"{{{{points['{name}'][0]}}}}", str(round(px, 1)))
        svg = svg.replace(f"{{{{points['{name}'][1]}}}}", str(round(py, 1)))
    for key, val in traj.items():
        svg = svg.replace(f"{{{{traj['{key}'][0]}}}}", str(val[0]))
        svg = svg.replace(f"{{{{traj['{key}'][1]}}}}", str(val[1]))

    return svg


# ============================================================
# 3. 生成试卷嵌入预览 HTML
# ============================================================
def build_exam_html(svg_content: str) -> str:
    # 去掉 SVG XML 声明
    svg_inline = svg_content
    for pat in ['<?xml version="1.0" encoding="UTF-8"?>\n',
                '<?xml version="1.0" encoding="UTF-8"?>']:
        svg_inline = svg_inline.replace(pat, '')

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>物理试卷预览 - 火星卫星轨道题</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:#f5f5f5;
    font-family:"SimSun","Noto Sans SC",serif;
    color:#222;
    padding:24px;
  }}
  .preview-note {{
    max-width:700px;
    margin:0 auto 18px;
    background:#fff8e1;
    border-left:4px solid #fbc02d;
    padding:10px 16px;
    font-size:13px;
    color:#666;
    border-radius:4px;
  }}
  .paper {{
    max-width:700px;
    margin:0 auto;
    background:#fff;
    padding:40px 54px 48px;
    box-shadow:0 2px 12px rgba(0,0,0,0.10);
    border-radius:4px;
  }}
  .paper-header {{
    text-align:center;
    padding-bottom:14px;
    margin-bottom:24px;
    border-bottom:2.5px solid #222;
  }}
  .paper-header h1 {{
    font-size:20px;
    font-weight:bold;
    letter-spacing:8px;
    color:#222;
  }}
  .paper-header .meta {{
    font-size:13px;
    color:#555;
    margin-top:8px;
  }}
  .q-number {{
    font-size:17px;
    font-weight:bold;
    display:inline;
  }}
  .question {{
    font-size:17px;
    line-height:2;
    margin:16px 0;
    text-indent:0;
  }}
  .question em {{
    font-style:italic;
    font-family:"Times New Roman","Noto Sans SC",serif;
  }}
  .figure-wrap {{
    text-align:center;
    margin:20px 0 16px;
    padding:12px 0;
  }}
  .figure-wrap svg {{
    width:420px;
    max-width:100%;
    height:auto;
    border:1px solid #d0d0d0;
    border-radius:3px;
    background:#fff;
  }}
  .fig-caption {{
    font-size:14px;
    color:#555;
    margin-top:8px;
  }}
  .sub-q {{
    font-size:16px;
    line-height:2.2;
    margin:10px 0;
    padding-left:1em;
  }}
  .options {{
    margin:14px 0 10px 2em;
    font-size:16px;
    line-height:2.4;
  }}
  .options li {{
    list-style:none;
    margin-bottom:6px;
  }}
  .options strong {{
    font-weight:bold;
    margin-right:6px;
  }}
  .page-footer {{
    margin-top:36px;
    padding-top:12px;
    border-top:1px solid #ccc;
    font-size:12px;
    color:#888;
    text-align:center;
  }}
  @media print {{
    body {{ background:#fff; padding:0; }}
    .paper {{ box-shadow:none; padding:20px 36px; }}
    .preview-note {{ display:none; }}
  }}
</style>
</head>
<body>

<div class="preview-note">
  ⚙️ 预览说明：这是用 Python + OpenCV 分析物理题图后自动生成的矢量 SVG，
  所有文字均为可编辑的 &lt;text&gt; 元素，可直接在 Inkscape / Illustrator 中修改。
</div>

<div class="paper">
  <div class="paper-header">
    <h1>高 中 物 理 试 卷</h1>
    <div class="meta">
      学校：___________&nbsp;&nbsp;
      姓名：___________&nbsp;&nbsp;
      考号：___________&nbsp;&nbsp;
      得分：___________
    </div>
  </div>

  <div class="question">
    <span class="q-number">16.</span>（12分）已知火星的质量约为地球质量的0.1倍，
    半径约为地球半径的0.5倍。若有一卫星绕火星做椭圆运动，
    其轨道如图所示。图中 <em>O</em> 为火星中心，
    <em>I</em>、<em>II</em>、<em>III</em> 为三条不同的可能轨道，
    <em>S</em>、<em>Q</em>、<em>P</em> 为卫星在轨道上的三个位置。
    已知卫星在轨道 <em>I</em> 上经过 <em>P</em> 点时的速率为 <em>v</em><sub>P</sub>。
  </div>

  <div class="figure-wrap">
    {svg_inline}
    <div class="fig-caption">图8 &nbsp; 卫星绕火星运动轨道示意图</div>
  </div>

  <div class="question" style="margin-top:0;">
    回答下列问题：
  </div>

  <div class="sub-q">
    （1）若卫星在轨道 <em>II</em> 上运动，经过 <em>P</em> 点时的速率
    <em>v</em><sub>P2</sub> 与 <em>v</em><sub>P</sub> 的大小关系为 ________；
  </div>
  <div class="sub-q">
    （2）若卫星从轨道 <em>III</em> 变轨到轨道 <em>II</em>，
    需要在 <em>Q</em> 点施加何种方向的作用力？答：________；
  </div>
  <div class="sub-q">
    （3）已知火星自转周期与地球相近，若火星同步卫星的轨道半径为 <em>r</em>，
    则 <em>r</em> 与火星半径 <em>R</em><sub>火</sub> 的比值约为 ________。
  </div>

  <div class="options">
    <li><strong>A.</strong> <em>v</em><sub>P2</sub> &gt; <em>v</em><sub>P</sub>，
      需要在 <em>Q</em> 点施加指向火星的作用力</li>
    <li><strong>B.</strong> <em>v</em><sub>P2</sub> &lt; <em>v</em><sub>P</sub>，
      需要在 <em>Q</em> 点施加背离火星的作用力</li>
    <li><strong>C.</strong> 同步卫星轨道半径 <em>r</em> ≈ 6.7 <em>R</em><sub>火</sub></li>
    <li><strong>D.</strong> 同步卫星轨道半径 <em>r</em> ≈ 2.4 <em>R</em><sub>火</sub></li>
  </div>

  <div class="page-footer">
    第 4 页（共 6 页）&nbsp;&nbsp;|&nbsp;&nbsp;物理试卷（人教版·必修二）
  </div>
</div>

</body>
</html>"""


# ============================================================
# main
# ============================================================
def main():
    print("=" * 50)
    print("物理题图 → 试卷风格 SVG 转换器 v3")
    print("=" * 50)

    print("\n[1/3] 分析图像...")
    analysis = analyze_image(INPUT_IMG)
    print(f"  火星中心: ({analysis['mars']['cx']}, {analysis['mars']['cy']})")
    print(f"  轨道半径: {analysis['orbits']}")
    with open(OUTPUT_DIR / "analysis_v3.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print("\n[2/3] 生成试卷风格 SVG...")
    svg = build_svg(analysis)
    svg_path = OUTPUT_DIR / "mars_exam_final.svg"
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  输出: {svg_path}")

    print("\n[3/3] 生成试卷预览 HTML...")
    html = build_exam_html(svg)
    html_path = OUTPUT_DIR / "exam_preview.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  输出: {html_path}")

    print(f"\n{'=' * 50}")
    print(f"完成!")
    print(f"  打开 exam_preview.html 查看试卷嵌入效果")
    print(f"  SVG 文件 mars_exam_final.svg 可直接导入 Inkscape/Illustrator 编辑")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
