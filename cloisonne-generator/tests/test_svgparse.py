# -*- coding: utf-8 -*-
"""测试svgpathtools解析VTracer输出"""
import svgpathtools

paths, attributes = svgpathtools.svg2paths("output/vtracer_test.svg")
print(f"解析到 {len(paths)} 条path")
for i, p in enumerate(paths):
    seg_types = {type(s).__name__ for s in p}
    fill = attributes[i].get("fill")
    print(f"  Path {i}: 段数={len(p)}, fill={fill}, 段类型={seg_types}")
    print(f"    起点=({p.start.real:.1f},{p.start.imag:.1f}), 终点=({p.end.real:.1f},{p.end.imag:.1f})")
