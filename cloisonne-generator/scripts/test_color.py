# -*- coding: utf-8 -*-
"""
scripts/test_color.py - 彩色模式回归测试 (V2.3 第16/44阶段)
- 对 examples/test01-04 + test_pattern 运行 CloisonnePipeline
- 收集: regions/boundaries/curves/self_intersection/runtime
- 与 V2.2 基线对比, 要求无明显回归
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline import CloisonnePipeline
from backend.result_schema import normalize_result, summarize_result

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(BASE, "examples")

CASES = [
    ("Test01 两色", os.path.join(EX, "test01_two_colors.png")),
    ("Test02 三色", os.path.join(EX, "test02_three_colors.png")),
    ("Test03 花", os.path.join(EX, "test03_flower.png")),
    ("Test04 猫", os.path.join(EX, "test04_cat.png")),
    ("TestPattern", os.path.join(EX, "test_pattern.png")),
]

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
}


def main():
    print("=" * 80)
    print("彩色模式回归测试 (V2.3 第16阶段)")
    print("=" * 80)
    hdr = f"{'用例':<16}{'regions':<9}{'boundaries':<11}{'curves':<8}{'自交':<7}{'runtime(s)':<10}"
    print(hdr)
    print("-" * 80)

    results = []
    for name, path in CASES:
        if not os.path.exists(path):
            print(f"[SKIP] {name}: {path} 不存在")
            continue
        with open(path, "rb") as f:
            img_bytes = f.read()
        pipe = CloisonnePipeline(dict(CONFIG))
        t0 = time.time()
        result = pipe.run(img_bytes, output_width_mm=100, img_format="png")
        runtime = time.time() - t0
        n = normalize_result(result)
        s = summarize_result(n)
        s["runtime_s"] = round(runtime, 3)
        results.append({"case": name, **s})
        print(f"{name:<16}{s['regions']:<9}{s['boundaries']:<11}{s['curves']:<8}"
              f"{s['self_intersections']:<7}{s['runtime_s']:<10}")

    with open(os.path.join(BASE, "results", "color_regression_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: results/color_regression_results.json")


if __name__ == "__main__":
    main()
