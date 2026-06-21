"""
试卷级物理图 SVG 直接生成器
- 参数手工校准，符合高考物理图规范
- 输出可编辑 SVG + 试卷预览 HTML
"""

from pathlib import Path

OUT = Path(r"D:\brain\eyes\SVG")
OUT.mkdir(parents=True, exist_ok=True)

W, H = 440, 360
# 火星中心
CX, CY = 220, 180
MARS_R = 22
# 轨道半径（从中心算起）
ORBITS = [72, 112, 150]
FONT = "SimSun, Noto Sans SC, serif"

# 点位置
POINTS = {
    "S": (CX,     CY - ORBITS[2] + 6),
    "Q": (CX + 52, CY - ORBITS[1] + 28),
    "P": (CX + 12, CY + ORBITS[2] - 2),
    "O": (CX + 5,  CY - MARS_R - 10),
}

# 轨迹 I 贝塞尔
TRAJ = {
    "sx": CX - 180, "sy": CY - 68,
    "cx": CX - 65,  "cy": CY + 38,
    "ex": CX + 10,  "ey": CY + ORBITS[2] - 4,
}


def make_svg():
    parts = []
    # defs
    parts.append(f'''<defs>
  <marker id="arr" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto-start-reverse">
    <polygon points="0 0,7 2.5,0 5" fill="#222" stroke="none"/>
  </marker>
  <style>
    text {{ font-family: {FONT}; fill: #222; }}
  </style>
</defs>''')

    # 轨道虚线（从外到内）
    for i, r in enumerate(reversed(ORBITS)):
        parts.append(
            f'<circle cx="{CX}" cy="{CY}" r="{r}" '
            f'fill="none" stroke="#555" stroke-width="1" '
            f'stroke-dasharray="5,3"/>'
        )
    # 轨道标签
    parts.append(f'<text x="{CX+ORBITS[2]-12}" y="{CY+ORBITS[2]+15}" font-size="13" fill="#555">III</text>')
    parts.append(f'<text x="{CX+ORBITS[1]+8}"  y="{CY-ORBITS[1]+26}" font-size="13" fill="#555">II</text>')

    # 火星
    parts.append(f'''<g id="mars">
  <circle cx="{CX}" cy="{CY}" r="{MARS_R}" fill="none" stroke="#222" stroke-width="1.5"/>
  <text x="{CX}" y="{CY}" font-size="15" text-anchor="middle" dominant-baseline="central">火星</text>
</g>''')

    # 点 S Q P
    for name, (px, py) in POINTS.items():
        if name == "O":
            parts.append(f'''<g id="pt-O">
  <circle cx="{round(px,1)}" cy="{round(py,1)}" r="2.2" fill="#666"/>
  <text x="{round(px+5,1)}" y="{round(py+3,1)}" font-size="12" fill="#666">O</text>
</g>''')
        else:
            parts.append(f'''<g id="pt-{name.lower()}">
  <circle cx="{round(px,1)}" cy="{round(py,1)}" r="3.4" fill="#222"/>
  <text x="{round(px+7,1)}" y="{round(py-4,1)}" font-size="15">{name}</text>
</g>''')

    # 轨迹 I
    t = TRAJ
    parts.append(f'''<path d="M {t["sx"]} {t["sy"]} Q {t["cx"]} {t["cy"]}, {t["ex"]} {t["ey"]}"
   fill="none" stroke="#222" stroke-width="1.5" marker-end="url(#arr)"/>''')
    parts.append(
        f'<text x="{(t["sx"]+t["cx"])//2 - 8}" '
        f'y="{(t["sy"]+t["cy"])//2}" font-size="13">I</text>'
    )

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {W} {H}"
     width="{W}px" height="{H}px">
  {''.join("  " + l + "\n" for l in parts)}
</svg>'''


def make_html(svg):
    svg_in = svg.replace('<?xml version="1.0" encoding="UTF-8"?>\n', '')
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<title>物理试卷 · 火星轨道题</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:#f5f5f5;font-family:"SimSun","Noto Sans SC",serif;padding:20px}}
  .note{{max-width:660px;margin:0 auto 12px;background:#fffbea;border-left:4px solid #fbc02d;padding:9px 14px;font-size:12.5px;color:#666;border-radius:4px}}
  .paper{{max-width:660px;margin:0 auto;background:#fff;padding:32px 44px 40px;box-shadow:0 2px 10px rgba(0,0,0,0.09);border-radius:4px}}
  .ph{{text-align:center;padding-bottom:11px;margin-bottom:18px;border-bottom:2.5px solid #222}}
  .ph h1{{font-size:19px;font-weight:bold;letter-spacing:7px}}
  .ph .m{{font-size:12.5px;color:#555;margin-top:6px}}
  .q{{font-size:15.5px;line-height:1.95;margin:12px 0}}
  .q em{{font-style:italic;font-family:"Times New Roman","Noto Sans SC",serif}}
  .fig{{text-align:center;margin:16px 0 12px;padding:8px 0}}
  .fig svg{{width:380px;max-width:100%;height:auto;border:1px solid #d0d0d0;border-radius:3px;background:#fff}}
  .cap{{font-size:13.5px;color:#555;margin-top:6px}}
  .sq{{font-size:14.5px;line-height:2.1;margin:7px 0 7px 1em}}
  .op{{margin:10px 0 8px 2em;font-size:14.5px;line-height:2.3}}
  .op li{{list-style:none;margin-bottom:4px}}
  .op strong{{margin-right:5px}}
  .ft{{margin-top:28px;padding-top:10px;border-top:1px solid #ccc;font-size:12px;color:#888;text-align:center}}
  @media print{{body{{background:#fff;padding:0}}.paper{{box-shadow:none;padding:18px 30px}}.note{{display:none}}}}
</style>
</head>
<body>
<div class="note">SVG 文字均为 &lt;text&gt; 元素，可直接在 Inkscape/Illustrator 中选中修改。线宽 1.5px，符合高考物理图规范。</div>
<div class="paper">
  <div class="ph"><h1>高 中 物 理 试 卷</h1>
    <div class="m">学校：___________&nbsp;&nbsp;姓名：___________&nbsp;&nbsp;考号：___________&nbsp;&nbsp;得分：___________</div>
  </div>
  <div class="q"><strong>16.</strong>（12分）已知火星的质量约为地球质量的 0.1 倍，半径约为地球半径的 0.5 倍。若有一卫星绕火星做椭圆运动，其轨道如图所示。图中 <em>O</em> 为火星中心，<em>I</em>、<em>II</em>、<em>III</em> 为三条不同的可能轨道，<em>S</em>、<em>Q</em>、<em>P</em> 为卫星在轨道上的三个位置。已知卫星在轨道 <em>I</em> 上经过 <em>P</em> 点时的速率为 <em>v</em><sub>P</sub>。</div>
  <div class="fig">
    {svg_in}
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
    svg = make_svg()
    (OUT / "mars_exam_final.svg").write_text(svg, encoding="utf-8")
    print(f"SVG: {OUT / 'mars_exam_final.svg'}")

    html = make_html(svg)
    html_path = OUT / "exam_preview.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML: {html_path}")
    print("完成！")

if __name__ == "__main__":
    main()
