"""
测试 PaddleOCR 对物理题图片的文字识别能力
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Lib\site-packages")

from paddleocr import PaddleOCR
from pathlib import Path
import json

IMG = r"E:\Users\Administrator\Desktop\asset_007.jpg"
OUT = r"D:\brain\eyes\SVG\ocr_result.json"

print("初始化 PaddleOCR (中文)...")
ocr = PaddleOCR(use_textline_orientation=True, lang='ch')

print(f"识别图片: {IMG}")
result = ocr.ocr(IMG, cls=True)

lines = []
if result and len(result) > 0:
    for line in result[0]:
        box = line[0]          # 四个角点
        text = line[1][0]       # 识别文字
        conf = line[1][1]      # 置信度
        lines.append({
            "text": text,
            "confidence": round(conf, 4),
            "box": [[round(p[0],1), round(p[1],1)] for p in box]
        })
        print(f"  [{conf:.3f}] {text}")

print(f"\n共识别 {len(lines)} 个文字区域")
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(lines, f, ensure_ascii=False, indent=2)
print(f"结果已保存: {OUT}")
