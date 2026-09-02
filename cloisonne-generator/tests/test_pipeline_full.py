# -*- coding: utf-8 -*-
"""测试完整管线（Phase 4/5）"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline import CloisonnePipeline
import json

with open("examples/test_pattern.png", "rb") as f:
    img_bytes = f.read()

config = {
    "color_count": 3,
    "color_merge_delta_e": 8.0,
    "min_region_area_mm2": 1.0,
    "min_boundary_length_mm": 1.0,
    "simplify_tolerance_mm": 0.15,
    "wire_diameter_mm": 0.6,
    "min_wire_spacing_mm": 0.8,
    "min_radius_mm": 1.0,
}
pipeline = CloisonnePipeline(config)
result = pipeline.run(img_bytes, output_width_mm=100)

print("=== 管线结果 ===")
print("颜色数:", len(result["color_palette"]))
print("区域数:", len(result["regions"]))
print("边界数:", len(result["boundaries"]))
print("合并曲线数:", len(result["merged_curves"]))
val = {k: v for k, v in result["validation"].items() if not isinstance(v, list)}
print("验证:", json.dumps(val, ensure_ascii=False))
print("SVG长度:", len(result["svg"]))
print("DXF base64:", "有" if result.get("dxf_base64") else "无")
print("IBL文本长度:", len(result.get("ibl_text") or ""))
print("修复记录:", len(result.get("repair_records") or []))

print()
print("=== 合并曲线详情 ===")
for mc in result["merged_curves"][:8]:
    print(f"  {mc['id']}: 边界{mc['boundary_ids']} 段数={mc['segment_count']} 闭合={mc['closed']} 长度={mc['length_mm']}mm")

print()
print("=== IBL前30行 ===")
ibl = result.get("ibl_text") or ""
for line in ibl.split("\n")[:30]:
    print(line)
