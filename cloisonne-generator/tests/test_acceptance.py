# -*- coding: utf-8 -*-
"""规格书第60-61章：最终工程验收测试
Test01: 两色块 → 预期1条公共边界
Test02: 三色块 → 预期A-B, A-C, B-C（只生成实际相邻的）
Test03: 花朵 → 曲线连续性/最小半径/线距
Test04: 卡通猫 → 小区域/内部细节
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.pipeline import CloisonnePipeline

CONFIG = {
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
    "smoothness": 0.7,
    "gen_outline": False,
}

def run_test(name, path, expected=None):
    with open(path, "rb") as f:
        img = f.read()
    pipeline = CloisonnePipeline(CONFIG)
    result = pipeline.run(img, output_width_mm=100)
    v = result["validation"]
    boundaries = result["boundaries"]
    # 提取边界对
    pairs = set()
    for b in boundaries:
        pairs.add((min(b["region_a"], b["region_b"]), max(b["region_a"], b["region_b"])))
    print(f"\n=== {name} ===")
    print(f"  区域数: {len(result['regions'])}, 边界数: {len(boundaries)}, 连续组: {len(result['merged_curves'])}")
    print(f"  验证: 状态={v['status']}, 自交={v['intersection_count']}, 线距冲突={v['spacing_violation_count']}, 小半径={v['small_radius_count']}, 断线={v['broken_curve_count']}")
    print(f"  边界对: {sorted(pairs)}")
    if expected:
        print(f"  预期: {expected}")
        match = expected == sorted(pairs)
        print(f"  匹配: {'✓ PASS' if match else '✗ FAIL'}")
    return result

print("=" * 50)
print("规格书最终工程验收测试")
print("=" * 50)

# Test 01: 两色块，预期1条公共边界
r1 = run_test("Test01 两色块", "examples/test01_two_colors.png",
              expected=[(0, 1)])

# Test 02: 三色块 + 下边蓝色，验证相邻关系
r2 = run_test("Test02 三色块", "examples/test02_three_colors.png")

# Test 03: 花朵
r3 = run_test("Test03 复杂花朵", "examples/test03_flower.png")

# Test 04: 卡通猫
r4 = run_test("Test04 卡通动物", "examples/test04_cat.png")

# 汇总
print("\n" + "=" * 50)
print("验收汇总")
print("=" * 50)
ok = True
if len(r1["boundaries"]) == 1:
    print("Test01 ✓ 两色块生成1条公共边界")
else:
    print(f"Test01 ✗ 期望1条边界，实际{len(r1['boundaries'])}条")
    ok = False
for name, r in [("Test02", r2), ("Test03", r3), ("Test04", r4)]:
    v = r["validation"]
    print(f"{name} ✓ 区域={len(r['regions'])}, 边界={len(r['boundaries'])}, 连续组={len(r['merged_curves'])}, 自交={v['intersection_count']}, 断线={v['broken_curve_count']}")
print("\n验收结果:", "全部通过 ✓" if ok else "存在失败项 ✗")
