# -*- coding: utf-8 -*-
"""测试V2.0管线（VTracer引擎）"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.pipeline import CloisonnePipeline

with open("examples/test_pattern.png", "rb") as f:
    img_bytes = f.read()

config = {
    "color_precision": 6,
    "filter_speckle": 4,
    "mode": "spline",
    "hierarchical": "cutout",
    "min_region_area_mm2": 1.0,
    "min_boundary_length_mm": 1.0,
    "simplify_tolerance_mm": 0.15,
    "wire_diameter_mm": 0.6,
    "min_wire_spacing_mm": 0.8,
    "min_radius_mm": 1.0,
}
pipeline = CloisonnePipeline(config)
result = pipeline.run(img_bytes, output_width_mm=100, img_format="png")

print("=== V2.0 管线结果 (引擎: VTracer) ===")
print("颜色数:", len(result["color_palette"]))
print("区域数:", len(result["regions"]))
print("边界数:", len(result["boundaries"]))
print("合并曲线数:", len(result["merged_curves"]))
val = {k: v for k, v in result["validation"].items() if not isinstance(v, list)}
print("验证:", json.dumps(val, ensure_ascii=False))
print("SVG长度:", len(result["svg"]))
print("DXF base64:", "有" if result.get("dxf_base64") else "无")
print("IBL文本长度:", len(result.get("ibl_text") or ""))

print()
print("=== 合并曲线详情 ===")
for mc in result["merged_curves"][:8]:
    print(f"  {mc['id']}: 边界{mc['boundary_ids']} 段数={mc['segment_count']} 闭合={mc['closed']} 长度={mc['length_mm']}mm")

# 保存输出
with open("output/v2_test.svg", "w", encoding="utf-8") as f:
    f.write(result["svg"])
print("\nSVG已保存: output/v2_test.svg")
