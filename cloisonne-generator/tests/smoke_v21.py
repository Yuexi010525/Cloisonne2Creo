# -*- coding: utf-8 -*-
"""V2.1矢量SharedBoundary冒烟测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.pipeline import CloisonnePipeline

cfg = dict(color_precision=6, filter_speckle=4, hierarchical='cutout', mode='spline',
           min_region_area_mm2=1.0, min_boundary_length_mm=1.5, simplify_tolerance_mm=0.15,
           wire_diameter_mm=0.6, min_wire_spacing_mm=0.8, min_radius_mm=1.0,
           output_width_mm=100, generate_mode='cloisonne', smoothness=0.7, gen_outline=False)
pipe = CloisonnePipeline(config=cfg)
img = open('examples/test01_two_colors.png', 'rb').read()
res = pipe.run(img, output_width_mm=100, img_format='png')
print('区域:', len(res['regions']))
print('边界:', len(res['boundaries']))
for b in res['boundaries'][:5]:
    print(f"  {b['id']}: region {b['region_a']}-{b['region_b']} len={b['length_mm']} pts={b['point_count']}")
v = res['validation']
print('验证:', v['status'], '自交', v['intersection_count'], '线距', v['spacing_violation_count'])
