# -*- coding: utf-8 -*-
"""验证DXF/IBL/SVG导出文件"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline import CloisonnePipeline
from exporters.dxf_exporter import DXFExporter
from exporters.ibl_exporter import IBLExporter
from exporters.json_exporter import JSONExporter

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

# 保存SVG
with open("output/test_output.svg", "w", encoding="utf-8") as f:
    f.write(result["svg"])
print("SVG已保存: output/test_output.svg")

# 导出DXF
if result.get("dxf_base64"):
    import base64
    with open("output/test_output.dxf", "wb") as f:
        f.write(base64.b64decode(result["dxf_base64"]))
    print("DXF已保存: output/test_output.dxf")

    # 验证DXF文件
    import ezdxf
    doc = ezdxf.readfile("output/test_output.dxf")
    msp = doc.modelspace()
    entities = list(msp)
    print(f"DXF验证: 读取成功, 实体数={len(entities)}, 单位={doc.units}")
    from collections import Counter
    types = Counter(e.dxftype() for e in entities)
    print(f"  实体类型: {dict(types)}")
    layers = set(e.dxf.layer for e in entities if hasattr(e.dxf, 'layer'))
    print(f"  使用的图层: {layers}")

# 导出IBL
ibl = pipeline.get_ibl_bytes()
with open("output/test_output.ibl", "wb") as f:
    f.write(ibl)
print("IBL已保存: output/test_output.ibl")
print(f"IBL大小: {len(ibl)} bytes")

# 验证IBL格式
ibl_text = ibl.decode("utf-8")
sections = ibl_text.count("begin section")
curves = ibl_text.count("begin curve")
print(f"IBL验证: sections={sections}, curves={curves}")
# 检查坐标精度（不应出现超过4位小数的点）
import re
coords = re.findall(r'^\d+ ([\d.]+) ([\d.]+) 0.0000$', ibl_text, re.MULTILINE)
max_decimals = 0
for x, y in coords:
    for v in (x, y):
        if '.' in v:
            max_decimals = max(max_decimals, len(v.split('.')[1]))
print(f"IBL坐标最大小数位: {max_decimals} (应为4)")

# 导出JSON项目
project = JSONExporter.build_project_data(result, "test_project")
with open("output/test_project.json", "w", encoding="utf-8") as f:
    import json
    json.dump(project, f, ensure_ascii=False, indent=2)
print("JSON已保存: output/test_project.json")

print("\n=== 所有导出验证完成 ===")
