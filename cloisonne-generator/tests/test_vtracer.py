# -*- coding: utf-8 -*-
"""测试VTracer输出效果"""
import vtracer

# 读取测试图
with open("examples/test_pattern.png", "rb") as f:
    img_bytes = f.read()

# 用cutout模式 + spline（规格书V2.0推荐参数）
svg = vtracer.convert_raw_image_to_svg(
    img_bytes,
    colormode="color",
    hierarchical="cutout",
    mode="spline",
    filter_speckle=4,
    color_precision=6,
)

with open("output/vtracer_test.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print(f"SVG大小: {len(svg)} bytes")
print(f"SVG前500字符:")
print(svg[:500])
print()
# 统计path数量
import re
paths = re.findall(r'<path', svg)
print(f"Path数量: {len(paths)}")
# 统计颜色
fills = re.findall(r'fill="([^"]+)"', svg)
from collections import Counter
print(f"颜色数: {len(set(fills))}")
for c, n in Counter(fills).most_common(10):
    print(f"  {c}: {n}")
