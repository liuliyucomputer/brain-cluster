"""
物理题图 → 试卷风格 SVG 生成器 v4
- 直接构造 SVG，不用模板变量
- 输出可编辑矢量图 + 试卷预览 HTML
"""

import cv2, numpy as np
from pathlib import Path

INPUT_IMG = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUT = Path(r"D:\brain\eyes\SVG")
OUT.mkdir(parents=True, exist_ok=True)

CANVAS_W = 460
CANVAS_H = 380
FONT = "SimSun, Noto Sans SC, serif"


def analyze(img_path):
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    scale = min(CANVAS_W / w, CANVAS_H / h) * 0.82
    ox = (CANVAS_W - w * scale) / 2
    oy = (CANVAS_H - h * scale) / 2

    # 检测圆
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1.2, 30,
                                  50, 25, 15, min(w, h) // 2)
    mars = {"cx": CANVAS_W // 2, "cy": CANVAS_H // 2, "r": 32}
    orbit_rs = [78, 122, 166]   # 默认轨道半径
    if circles is not None:
        cs = sorted([(c[0], c[1], c[2]) for c in circles[0]], key=lambda x: x[2])
        if cs:
            # 最小圆当火星
            mx, my, mr = cs[0]
            mars = {
                "cx": round(mx * scale + ox, 1),
                "cy": round(my * scale + oy, 1),
                "r":  round(mr * scale, 1),
            }
            # 其余当轨道（取较大的几个）
            big = sorted([c[2] for c in cs], reverse=True)[:3]
            if len(big) >= 3:
                orbit_rs = [round(r * scale, 1) for r in big[::-1]]

    return {"mars": mars, "orbits": orbit_rs, "scale": scale, "offset": (ox, oy)}


def make_svg(a):
    M = a["mars"]
    ob = a["orbits"]
    cx, cy, mr = M["cx"], M["cy"], M["r"]

    # 点位置（相对火星中心）
    S  = (cx,     cy - ob[2] + 8)
    Q  = (cx + ob[1]*0.52, cy - ob[1]*0.38)
    P  = (cx + ob[2]*0.08, cy + ob[2] - 4)
    O  = (cx + 6, cy - mr - 10)

    # 轨迹 I 贝塞尔控制点
    TS = (cx - 200, cy - 80)
    TC = (cx - 70,  cy + 45)
    TE = (cx + 8,   cy + ob[2] - 6)

    lines = []
    lines.append(f'<circle cx="{cx}" cy="{cy}" r="{ob[2]}" fill="none" stroke="#555" stroke-width="1" stroke-dasharray="5,3"/>')
    lines.append(f'<circle cx="{cx}" cy="{cy}" r="{ob[1]}" fill="none" stroke="#555" stroke-width="1" stroke-dasharray="5,3"/>')
    lines.append(f'<circle cx="{cx}" cy="{cy}" r="{ob[0]}" fill="none" stroke="#555" stroke-width="1" stroke-dasharray="5,3"/>')
    lines.append(f'<text x="{cx + ob[2] - 15}" y="{cy + ob[2] + 16}" font-size="14" fill="#555">III</text>')
    lines.append(f'<text x="{cx + ob[1] + 8}"  y="{cy - ob[1] + 28}" font-size="14" fill="#555">II</text>')

    # 火星
    lines.append(f'''<g id="mars">
  <circle cx="{cx}" cy="{cy}" r="{mr}" fill="none" stroke="#222" stroke-width="1.6"/>
  <text x="{cx}" y="{cy}" font-size="16" text-anchor="middle" dominant-baseline="central">火星</text>
</g>''')

    # 点 S Q P
    for name, (px, py) in [("S", S), ("Q", Q), ("P", P)]:
        lines.append(f'''<g id="pt-{name.lower()}">
  <circle cx="{round(px,1)}" cy="{round(py,1)}" r="3.5" fill="#222"/>
  <text x="{round(px+7,1)}" y="{round(py-5,1)}" font-size="16">{name}</text>
</g>''')

    # 点 O
    lines.append(f'''<g id="pt-o">
  <circle cx="{round(O[0],1)}" cy="{round(O[1],1)}" r="2.5" fill="#666"/>
  <text x="{round(O[0]+6,1)}" y="{round(O[1]+3,1)}" font-size="13" fill="#666">O</text>
</g>''')

    # 轨迹 I
    lines.append(f'''<path d="M {TS[0]} {TS[1]} Q {TC[0]} {TC[1]}, {TE[0]} {TE[1]}"
       fill="none" stroke="#222" stroke-width="1.6"
       marker-end="url(#arr)"/>''')
    lines.append(f'<text x="{(TS[0]+TC[0])//2 - 8}" y="{(TS[1]+TC[1])//2}" font-size="14">I</text>')

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {CANVAS_W} {CANVAS_H}"
     width="{CANVAS_W}px" height="{CANVAS_H}px">
<defs>
  <marker id="arr" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto-start-reverse">
    <polygon points="0 0,7 2.5,0 5" fill="#222" stroke="none"/>
  </marker>
  <style>
    text {{ font-family: {FONT}; fill: #222; }}
  </style>
</defs>
{chr(10).join("  " + l for l in lines)}
</svg>'''
    return svg


def make_html(svg_str):
    svg_inline = svg_str.replace('<?xml version="1.0" encoding="UTF-8"?>\n', '')
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<title>物理试卷 · 火星轨道题</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:#f5f5f5;font-family:"SimSun","Noto Sans SC",serif;padding:24px}}
  .note{{max-width:680px;margin:0 auto 14px;background:#fffbea;border-left:4px solid #fbc02d;padding:10px 16px;font-size:13px;color:#666;border-radius:4px}}
  .paper{{max-width:680px;margin:0 auto;background:#fff;padding:36px 48px 44px;box-shadow:0 2px 12px rgba(0,0,0,0.1);border-radius:4px}}
  .ph{{text-align:center;padding-bottom:12px;margin-bottom:20px;border-bottom:2.5px solid #222}}
  .ph h1{{font-size:19px;font-weight:bold;letter-spacing:7px}}
  .ph .m{{font-size:13px;color:#555;margin-top:6px}}
  .q{{font-size:16px;line-height:2;margin:14px 0}}
  .q em{{font-style:italic;font-family:"Times New Roman","Noto Sans SC",serif}}
  .fig{{text-align:center;margin:18px 0;padding:10px 0}}
  .fig svg{{width:400px;max-width:100%;height:auto;border:1px solid #d0d0d0;border-radius:3px;background:#fff}}
  .cap{{font-size:14px;color:#555;margin-top:6px}}
  .sq{{font-size:15px;line-height:2.2;margin:8px 0 8px 1em}}
  .op{{margin:12px 0 10px 2em;font-size:15px;line-height:2.4}}
  .op li{{list-style:none;margin-bottom:5px}}
  .ft{{margin-top:32px;padding-top:10px;border-top:1px solid #ccc;font-size:12px;color:#888;text-align:center}}
  @media print{{body{{background:#fff;padding:0}}.paper{{box-shadow:none;padding:20px 32px}}.note{{display:none}}}}
</style>
</head>
<body>
<div class="note">⚙️ 预览：SVG 所有文字均为 &lt;text&gt; 元素，可直接在 Inkscape / Illustrator 中选中编辑。线宽 1.6px，符合高考物理试卷制图规范。</div>
<div class="paper">
  <div class="ph">
    <h1>高 中 物 理 试 卷</h1>
    <div class="m">学校：___________&nbsp;&nbsp;姓名：___________&nbsp;&nbsp;考号：___________&nbsp;&nbsp;得分：___________</div>
  </div>
  <div class="q"><strong>16.</strong>（12分）已知火星的质量约为地球质量的 0.1 倍，半径约为地球半径的 0.5 倍。若有一卫星绕火星做椭圆运动，其轨道如图所示。图中 <em>O</em> 为火星中心，<em>I</em>、<em>II</em>、<em>III</em> 为三条不同的可能轨道，<em>S</em>、<em>Q</em>、<em>P</em> 为卫星在轨道上的三个位置。已知卫星在轨道 <em>I</em> 上经过 <em>P</em> 点时的速率为 <em>v</em><sub>P</sub>。</div>
  <div class="fig">
    {svg_inline}
    <div class="cap">图 8&nbsp;&nbsp;卫星绕火星运动轨道示意图</div>
  </div>
  <div class="q" style="margin-top:0">回答下列问题：</div>
  <div class="sq">（1）若卫星在轨道 <em>II</em> 上运动，经过 <em>P</em> 点时的速率 <em>v</em><sub>P2</sub> 与 <em>v</em><sub>P</sub> 的大小关系为 ________；</div>
  <div class="sq">（2）若卫星从轨道 <em>III</em> 变轨到轨道 <em>II</em>，需要在 <em>Q</em> 点施加何种方向的作用力？答：________；</div>
  <div class="sq">（3）已知火星自转周期与地球相近，若火星同步卫星的轨道半径为 <em>r</em>，则 <em>r</em> 与火星半径 <em>R</em><sub>火</sub> 的比值约为 ________。</div>
  <div class="op">
    <li><strong>A.</strong> <em>v</em><sub>P2</sub> &gt; <em>v</em><sub>P</sub>，需要在 <em>Q</em> 点施加指向火星的作用力</li>
    <li><strong>B.</strong> <em>v</em><sub>P2</sub> &lt; <em>v</em><sub>P</sub>，需要在 <em>Q</em> 点施加背离火星的作用力</li>
    <li><strong>C.</strong> 同步卫星轨道半径 <em>r</em> ≈ 6.7 <em>R</em><sub>火</sub></li>
    <li><strong>D.</strong> 同步卫星轨道半径 <em>r</em> ≈ 2.4 <em>R</em><sub>火</sub></li>
  </div>
  <div class="ft">第 4 页（共 6 页）&nbsp;&nbsp;|&nbsp;&nbsp;物理试卷（人教版·必修二）</div>
</div>
</body>
</html>'''


def main():
    print("生成试卷风格物理图 SVG...")
    a = analyze(INPUT_IMG)
    print(f"  火星: ({a['mars']['cx']}, {a['mars']['cy']}) r={a['mars']['r']}")
    print(f"  轨道: {a['orbits']}")

    svg = make_svg(a)
    svg_path = OUT / "mars_exam_final.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(f"  SVG: {svg_path}")

    html = make_html(svg)
    html_path = OUT / "exam_preview.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  HTML: {html_path}")
    print("完成！打开 exam_preview.html 查看效果。")

if __name__ == "__main__":
    main()
