# -*- coding: utf-8 -*-
"""
物理题图 → 可编辑 SVG 转换器 v12 — 最终稳定版
已验证通过的技术方案:
- 标记点: 圆度排序Top-N (v8验证)
- 轨迹曲线: Canny+轮廓+B样条拟合 (v11验证)  
- OCR: RapidOCR (已验证)
- 轨道: 同心约束 (几何正确性)
"""
import cv2, numpy as np, json, os, sys

INPUT = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUT   = r"D:\brain\eyes\SVG"
SCALE = 3
FONT  = "'Noto Sans SC', SimSun, 'Microsoft YaHei', sans-serif"

img = cv2.imread(INPUT)
assert img is not None
H, W = img.shape[:2]
OW, OH = W*SCALE, H*SCALE
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# ========== 1. 火星圆心 ==========
mc = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
    param1=50, param2=30, minRadius=20, maxRadius=50)
mx0, my0, mr0 = [int(v) for v in mc[0][0]]
MX, MY, MR = mx0*SCALE, my0*SCALE, mr0*SCALE
print(f"火星({mx0},{my0}) r={mr0} -> ({MX},{MY})")

# ========== 2. 标记点 S/Q/P (宽松检测 + 圆度排序取Top3) ==========
bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]
cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cands = []
for c in cnts:
    a = cv2.contourArea(c)
    if not (3 < a < 150): continue
    p = cv2.arcLength(c, True)
    if p <= 0: continue
    circ = 4*np.pi*a/(p*p)
    if circ < 0.50: continue  # 宽松阈值，靠后续排序过滤
    M = cv2.moments(c)
    if M["m00"] <= 0: continue
    cx, cy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
    if np.hypot(cx-mx0, cy-my0) < mr0 * 0.85: continue  # 排除火星内
    cands.append({"cx": cx, "cy": cy, "area": a, "circ": circ})

# 按圆度降序取候选
cands.sort(key=lambda x: -x["circ"])
top = cands[:10]
# 筛选在火星垂线附近的
near = [t for t in top if abs(t["cx"] - mx0) < 50]

# S = 最上面的点, P = 最下面的点（在near列表中找）
ysorted = sorted(near, key=lambda t: t["cy"])
s_pt = ysorted[0] if ysorted else None
p_pt = ysorted[-1] if len(ysorted) > 1 else None

# Q = 在火星上方、S下方，最接近火星中心X坐标的点
q_candidates = [t for t in near if s_pt and s_pt["cy"] < t["cy"] < my0 and abs(t["cx"]-mx0) < 30]
if q_candidates:
    q_candidates.sort(key=lambda t: abs(t["cx"]-mx0))  # 取最靠近中线的
    q_pt = q_candidates[0]
else:
    # 回退：几何推断 Q 在火星正上方约 mr*1.8 距离处
    q_pt = {"cx": mx0 + 4, "cy": my0 - int(mr0 * 1.7), "area": 20, "circ": 0,
            "_inferred": True}

names = ["S","Q","P"]
markers = []
for name, pt in zip(names, [s_pt, q_pt, p_pt]):
    if pt is None:
        continue
    r_px = max(int(np.sqrt(pt.get("area",25))/np.pi*SCALE), int(4.5*SCALE))
    markers.append({"name": name, "cx": pt["cx"]*SCALE, "cy": pt["cy"]*SCALE,
                    "r": r_px, "circ": round(pt.get("circ",0), 3),
                    "raw_cx": pt["cx"], "raw_cy": pt["cy"],
                    "inferred": pt.get("_inferred", False)})
print(f"标记点: {[(m['name'], m['raw_cx'], m['raw_cy'], 'AUTO' if not m.get('inferred') else 'INFERRED') for m in markers]}")

# ========== 3. OCR ============
ocr_res = []
try:
    from rapidocr_onnxruntime import RapidOCR
    r, _ = RapidOCR()(img)
    if r:
        for box, txt, conf in r:
            txt = str(txt).strip()
            if txt:
                ocr_res.append({"text": txt,
                    "cx": int(np.mean([p[0] for p in box]))*SCALE,
                    "cy": int(np.mean([p[1] for p in box]))*SCALE})
except Exception as e:
    print(f"OCR异常(非致命): {e}")
print(f"OCR: {[o['text'] for o in ocr_res]}")

# ========== 4. 轨迹曲线 ==========
edges = cv2.Canny(gray, 40, 120)
lmask = np.zeros_like(edges); lmask[:, :int(W*0.72)] = 255
cv2.circle(lmask, (mx0, my0), int(mr0*1.6), 0, -1)
el = cv2.bitwise_and(edges, lmask)
el = cv2.morphologyEx(el, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
cand_cts, _ = cv2.findContours(el, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
bc, blen = None, 0
for c in cand_cts:
    al = cv2.arcLength(c, False); ar = cv2.contourArea(c)
    if al > 70 and ar < 5000 and al > blen: bc, blen = c, al

traj_pts_raw = None
if bc is not None:
    raw_pts = bc.reshape(-1, 2)
    n = len(raw_pts)
    si = int(np.argmin(raw_pts[:, 0]))
    vis = {si}; ordered = [raw_pts[si].tolist()]; cur = si
    for _ in range(n-1):
        cp = raw_pts[cur]; ni_, nd_ = -1, float('inf')
        for j in range(n):
            if j not in vis:
                d = np.hypot(raw_pts[j,0]-cp[0], raw_pts[j,1]-cp[1])
                if d < nd_: nd_, ni_ = d, j
        if ni_ >= 0:
            ordered.append(raw_pts[ni_].tolist()); cur = ni_; vis.add(ni_)
    arr = np.array(ordered)
    if len(arr) > 30:
        idx = np.linspace(0, len(arr)-1, 30, dtype=int); arr = arr[idx]
    traj_pts_raw = [(float(p[0]*SCALE), float(p[1]*SCALE)) for p in arr]
    print(f"轨迹: {len(bc.reshape(-1,2))}原始→{len(arr)}采样点 弧长{blen:.0f}")

def smooth_path(pts):
    if not pts or len(pts) < 3: return None
    A = np.array(pts)
    try:
        from scipy.interpolate import splprep, splev
        tk, u = splprep([A[:,0],A[:,1]], s=len(pts)*4, k=3)
        un = np.linspace(u.min(), u.max(), max(len(pts)*3, 80))
        xn, yn = splev(un, tk)
        d = [f"M{xn[0]:.1f},{yn[0]:.1f}"]
        for i in range(1, len(xn)-2, 2):
            if i+2 < len(xn): d.append(f"C{xn[i]:.1f},{yn[i]:.1f} {xn[i+1]:.1f},{yn[i+1]:.1f} {xn[i+2]:.1f},{yn[i+2]:.1f}")
        for i in range(len(xn)-len(xn)%2, len(xn)): d.append(f"L{xn[i]:.1f},{yn[i]:.1f}")
        return " ".join(d)
    except Exception:
        d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
        for p in pts[1:]: d.append(f"L{p[0]:.1f},{p[1]:.1f}")
        return " ".join(d)

# ========== 5. 构建SVG ==========
sw = round(1.5*SCALE, 1); tw = round(1.8*SCALE, 1)
fs = int(14*SCALE); fb = int(15*SCALE); fl = int(13*SCALE)
ds = f"{int(SCALE*4)},{int(SCALE*3)}"
orbs = [("I",int(MR*3.25)), ("II",int(MR*2.28)), ("III",int(MR*1.52))]

S = []; app = S.append
app('<?xml version="1.0" encoding="UTF-8"?>')
app(f'<svg xmlns="http://www.w3.org/2000/svg" width="{OW}" height="{OH}" viewBox="0 0 {OW} {OH}" style="background:#fff">')
app('<defs><marker id="a" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#CC0000"/></marker></defs>')
app(f'<style>.o{{stroke:#000;fill:none;stroke-dasharray:{ds};stroke-width:{sw}}}.t{{stroke:#CC0000;fill:none;stroke-width:{tw};marker-end:url(#a)}}.b{{fill:#fff;stroke:#000;stroke-width:{sw}}}.d{{fill:#000}}.tx{{font-size:{fs}px;font-family:{FONT};fill:#000}}.tb{{font-size:{fb}px;font-family:{FONT};fill:#000;font-weight:bold}}.tl{{font-size:{fl}px;font-family:{FONT};fill:#000;font-style:italic}}</style>')
app(f'<rect width="{OW}" height="{OH}" fill="#fff"/>')

for nm, rd in orbs:
    app(f'<g data-orbit="{nm}"><circle cx="{MX}" cy="{MY}" r="{rd}" class="o"/><text x="{MX+rd+9*SCALE:.0f}" y="{MY+rd*0.44:.0f}" class="tl">{nm}</text></g>')

app(f'<g data-type="planet"><circle cx="{MX}" cy="{MY}" r="{MR}" class="b"/><text x="{MX}" y="{MY+5*SCALE}" class="tb" text-anchor="middle">火星</text></g>')

for mk in markers:
    off = 11*SCALE
    app(f'<g data-marker="{mk["name"]}"><circle cx="{mk["cx"]:.0f}" cy="{mk["cy"]:.0f}" r="{mk["r"]}" class="d"/><text x="{mk["cx"]+off:.0f}" y="{mk["cy"]+5*SCALE:.0f}" class="tb">{mk["name"]}</text></g>')

pd = smooth_path(traj_pts_raw)
if pd: app(f'<!-- traj {len(traj_pts_raw)}pts --><path d="{pd}" class="t"/>')
else: app('<!-- WARNING: no trajectory -->')

app('</svg>')
svg_out = "\n".join(S)

os.makedirs(OUT, exist_ok=True)
svp = os.path.join(OUT, "mars_orbit_v12.svg")
with open(svp, 'w', encoding='utf-8') as f: f.write(svg_out)
print(f"\nSVG: {svp}")

analysis = {
    "version": "v12-final",
    "mars": {"cx": int(MX), "cy": int(MY), "r": int(MR)},
    "markers": [{"name": m["name"], "cx": m["cx"], "cy": m["cy"], "circ": m["circ"]} for m in markers],
    "ocr": [o["text"] for o in ocr_res],
    "orbits": [{"n": n, "r": r} for n,r in orbs],
    "trajectory": {"pts": len(traj_pts_raw) if traj_pts_raw else 0}
}
with open(os.path.join(OUT, "analysis_v12.json"), 'w', encoding='utf-8') as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)
print("完成!")
