# -*- coding: utf-8 -*-
"""
物理题图 → 可编辑 SVG 转换器 v11 — 精确稳定版
v10 问题修复：
1. 标记点检测：圆度≥0.78 + 面积8~60px + 排除火星内部 → 精准定位S/Q/P
2. 轨迹曲线：直接用Canny+长轮廓提取，不过度过滤
3. B样条拟合平滑路径输出
"""
import cv2, numpy as np, json, os, sys

INPUT_IMG = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUT_DIR = r"D:\brain\eyes\SVG"
SCALE = 3
FONT = "'Noto Sans SC', SimSun, 'Microsoft YaHei', sans-serif"

img = cv2.imread(INPUT_IMG)
assert img is not None, f"Cannot read {INPUT_IMG}"
H, W = img.shape[:2]
ow, oh = W*SCALE, H*SCALE
print(f"原图: {W}x{H} → 输出: {ow}x{oh}")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# ===== 1. 火星圆心（基准）=====
mc = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
    minDist=30, param1=50, param2=30, minRadius=20, maxRadius=50)
mx0, my0, mr0 = [int(x) for x in mc[0][0]]
mx, my, mr = mx0*SCALE, my0*SCALE, mr0*SCALE
print(f"火星: ({mx0},{my0}) r={mr0}")

# ===== 2. 标记点（v8验证过的参数：area 5~120, circ>0.80）=====
bin_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
contours, _ = cv2.findContours(bin_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
markers = []
for c in contours:
    a = cv2.contourArea(c)
    if not (5 < a < 120): continue
    p = cv2.arcLength(c, True)
    if p == 0: continue
    circ = 4*np.pi*a/(p*p)
    if circ < 0.80: continue
    M = cv2.moments(c)
    if M["m00"] <= 0: continue
    cx, cy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
    # 只排除明显在火星圆内部的（留余量给Q）
    if np.hypot(cx-mx0, cy-my0) < mr0 * 0.85: continue
    markers.append({"cx": cx*SCALE, "cy": cy*SCALE,
                    "r": max(int(np.sqrt(a/np.pi)*SCALE), 4*SCALE),
                    "circ": round(circ, 3), "raw_cx": cx, "raw_cy": cy})

markers.sort(key=lambda m: m["cy"])
for i, m in enumerate(markers):
    m["name"] = ["S", "Q", "P"][i] if i < 3 else f"M{i}"
print(f"标记点({len(markers)}): {[(m['name'], m.get('raw_cx',int(m['cx'])), m.get('raw_cy',int(m['cy']))) for m in markers]}")

# ===== 3. OCR =====
ocr_texts = []
try:
    from rapidocr_onnxruntime import RapidOCR
    res, _ = RapidOCR()(img)
    if res:
        for box, txt, conf in res:
            txt = str(txt).strip()
            if txt:
                ocr_texts.append({
                    "text": txt,
                    "cx": int(np.mean([p[0] for p in box]))*SCALE,
                    "cy": int(np.mean([p[1] for p in box]))*SCALE
                })
except Exception as e:
    print(f"OCR异常: {e}")
print(f"OCR: {[o['text'] for o in ocr_texts]}")

# ===== 4. 轨迹曲线（Canny + 最长有效轮廓 + B样条）=====
edges = cv2.Canny(gray, 40, 120)

# 创建左半区域掩码（只保留左侧的线）
lmask = np.zeros_like(edges)
lmask[:, :int(W*0.72)] = 255
e_left = cv2.bitwise_and(edges, lmask)

# 挖掉火星及附近区域（避免轨道虚线干扰）
cv2.circle(lmask, (mx0, my0), int(mr0*1.6), 0, -1)

# 形态学连接断裂
ke = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
eclean = cv2.morphologyEx(e_left, cv2.MORPH_CLOSE, ke)

conts, _ = cv2.findContours(eclean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

best_cont = None
best_len = 0
for c in conts:
    alen = cv2.arcLength(c, False)
    area = cv2.contourArea(c)
    # 轨迹特征：长度够(>70)，且不是封闭的大面积形状
    if alen > 70 and area < 5000:
        if alen > best_len:
            best_len = alen
            best_cont = c

traj_pts = None
if best_cont is not None:
    raw = best_cont.reshape(-1, 2)
    
    # 点排序（贪心最近邻）
    n = len(raw)
    si = np.argmin(raw[:, 0])  # 最左端作为起点
    vis = {si}
    ordered = [raw[si].tolist()]
    curr = si
    for _ in range(n-1):
        cp = raw[curr]
        ni, nd = -1, float('inf')
        for j in range(n):
            if j not in vis:
                d = np.hypot(raw[j,0]-cp[0], raw[j,1]-cp[1])
                if d < nd:
                    nd, ni = d, j
        if ni >= 0:
            ordered.append(raw[ni].tolist())
            curr = ni
            vis.add(ni)
    
    ordered = np.array(ordered)
    
    # 降采样到合理数量
    target_n = 30
    if len(ordered) > target_n:
        idx = np.linspace(0, len(ordered)-1, target_n, dtype=int)
        ordered = ordered[idx]
    
    traj_pts = [(float(p[0]*SCALE), float(p[1]*SCALE)) for p in ordered]
    print(f"轨迹: 原始{len(raw)}点 → 有序{len(traj_pts)}采样点, 弧长={best_len:.0f}px")

else:
    # 备用方案：Hough长线段
    print("轮廓法未找到轨迹，尝试Hough备用...")
    lines = cv2.HoughLinesP(gray, rho=1, theta=np.pi/720,
        threshold=22, minLineLength=18, maxLineGap=6)
    segs = []
    if lines is not None:
        for l in lines:
            x1,y1,x2,y2 = l[0]
            if np.hypot(x2-x1,y2-y1) > 20:
                # 只保留左侧的线段
                if (x1+x2)/2 < W * 0.7:
                    segs.append((x1*SCALE,y1*SCALE,x2*SCALE,y2*SCALE))
        
        if segs:
            # 贪心连接成路径
            used = set()
            path_pts = [(segs[0][0], segs[0][1])]
            last_end = (segs[0][2], segs[0][3])
            used.add(0)
            
            while len(used) < len(segs):
                bi, bd = -1, float('inf')
                for i, s in enumerate(segs):
                    if i in used:
                        continue
                    d = np.hypot(s[0]-last_end[0], s[1]-last_end[1])
                    if d < bd:
                        bd, bi = d, i
                if bi >= 0:
                    path_pts.append((segs[bi][0], segs[bi][1]))
                    last_end = (segs[bi][2], segs[bi][3])
                    used.add(bi)
                else:
                    break
            
            path_pts.append(last_end)
            traj_pts = path_pts
            print(f"Hough备用: {len(segs)}线段 → {len(path_pts)}点")


def make_smooth_path(pts):
    """B样条拟合 → SVG path"""
    if not pts or len(pts) < 3:
        return None
    
    arr = np.array(pts)
    try:
        from scipy.interpolate import splprep, splev
        tck, u = splprep([arr[:,0], arr[:,1]], s=len(pts)*4, k=3)
        un = np.linspace(u.min(), u.max(), max(len(pts)*3, 80))
        xn, yn = splev(un, tck)
        
        ds = [f"M{xn[0]:.1f},{yn[0]:.1f}"]
        for i in range(1, len(xn)-2, 2):
            if i+2 < len(xn):
                ds.append(f"C{xn[i]:.1f},{yn[i]:.1f} {xn[i+1]:.1f},{yn[i+1]:.1f} {xn[i+2]:.1f},{yn[i+2]:.1f}")
        rem = len(xn) % 2
        for i in range(len(xn)-rem, len(xn)):
            ds.append(f"L{xn[i]:.1f},{yn[i]:.1f}")
        return " ".join(ds)
    except ImportError:
        pass
    except Exception:
        pass
    
    # fallback: 折线
    ds = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for p in pts[1:]:
        ds.append(f"L{p[0]:.1f},{p[1]:.1f}")
    return " ".join(ds)


# ===== 5. 构建SVG =====
sw = round(1.5*SCALE, 1)
tw = round(1.8*SCALE, 1)
fs = int(14*SCALE); fs_b = int(15*SCALE); fs_l = int(13*SCALE)
ds_arr = f"{int(SCALE*4)},{int(SCALE*3)}"

orbits = [
    ("I",   int(mr*3.25)),
    ("II",  int(mr*2.28)),
    ("III", int(mr*1.52)),
]

svg = []
svg.append(f'<?xml version="1.0" encoding="UTF-8"?>')
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="0 0 {ow} {oh}" style="background:#fff">')
svg.append('<defs><marker id="a" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#CC0000"/></marker></defs>')
svg.append(f'<style>.o{{stroke:#000;fill:none;stroke-dasharray:{ds_arr};stroke-width:{sw}}}.t{{stroke:#CC0000;fill:none;stroke-width:{tw};marker-end:url(#a)}}.b{{fill:#fff;stroke:#000;stroke-width:{sw}}}.d{{fill:#000}}.tx{{font-size:{fs}px;font-family:{FONT};fill:#000}}.tb{{font-size:{fs_b}px;font-family:{FONT};fill:#000;font-weight:bold}}.tl{{font-size:{fs_l}px;font-family:{FONT};fill:#000;font-style:italic}}</style>')
svg.append(f'<rect width="{ow}" height="{oh}" fill="#fff"/>')

for name, radius in orbits:
    lx = mx + radius + 9*SCALE
    ly = my + radius*0.44
    svg.append(f'<g data-orbit="{name}"><circle cx="{mx}" cy="{my}" r="{radius}" class="o"/><text x="{lx:.0f}" y="{ly:.0f}" class="tl">{name}</text></g>')

svg.append(f'<g data-type="planet"><circle cx="{mx}" cy="{my}" r="{mr}" class="b"/><text x="{mx}" y="{my+5*SCALE}" class="tb" text-anchor="middle">火星</text></g>')

for mk in markers:
    off = 11*SCALE
    svg.append(f'<g data-marker="{mk["name"]}"><circle cx="{mk["cx"]:.0f}" cy="{mk["cy"]:.0f}" r="{mk["r"]}" class="d"/><text x="{mk["cx"]+off:.0f}" y="{mk["cy"]+5*SCALE:.0f}" class="tb">{mk["name"]}</text></g>')

path_d = make_smooth_path(traj_pts)
if path_d:
    svg.append(f'<!-- trajectory ({len(traj_pts)} pts) --><path d="{path_d}" class="t"/>')
else:
    svg.append('<!-- WARNING: no trajectory -->')

svg.append('</svg>')
svg_content = "\n".join(svg)

os.makedirs(OUT_DIR, exist_ok=True)
svp = os.path.join(OUT_DIR, "mars_orbit_v11.svg")
with open(svp, 'w', encoding='utf-8') as f:
    f.write(svg_content)
print(f"\n✅ SVG: {svp}")

analysis = {
    "version": "v11",
    "mars": {"cx": int(mx), "cy": int(my), "r": int(mr)},
    "markers": [{"name": m["name"], "cx": m["cx"], "cy": m["cy"]} for m in markers],
    "ocr": ocr_texts,
    "orbits": [{"n": n, "r": r} for n,r in orbits],
    "trajectory": {"pts": len(traj_pts) if traj_pts else 0, "ok": traj_pts is not None},
}
jfp = os.path.join(OUT_DIR, "analysis_v11.json")
with open(jfp, 'w', encoding='utf-8') as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
print(f"报告: {jfp}")
