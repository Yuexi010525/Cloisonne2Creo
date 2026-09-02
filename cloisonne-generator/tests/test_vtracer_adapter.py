# -*- coding: utf-8 -*-
"""测试VTracerAdapter"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.segmentation.vtracer_adapter import VTracerAdapter

with open("examples/test_pattern.png", "rb") as f:
    img_bytes = f.read()

adapter = VTracerAdapter(color_precision=6, filter_speckle=4, mode="spline", hierarchical="cutout")
svg = adapter.convert(img_bytes, "png")
print("SVG生成:", len(svg), "bytes, 尺寸:", adapter.width, "x", adapter.height)
regions = adapter.parse_regions()
print("区域数:", len(regions))
for r in regions:
    print(f"  Region {r['id']}: color={r['color']}, area={r['area_px']:.0f}px, closed={r['closed']}")
print("label_map shape:", adapter.label_map.shape)
print("唯一ID:", sorted(set(adapter.label_map.flatten().tolist())))
