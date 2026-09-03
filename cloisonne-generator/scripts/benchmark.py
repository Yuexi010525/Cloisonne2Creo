# -*- coding: utf-8 -*-
"""
scripts/benchmark.py - 基准测试工具 (V2.3 第45阶段)
- 对 Color(Test01-04) 和 LineArt(粗线/圆环/十字/用户线稿) 各模式跑
- 记录: image size / mode / runtime / regions / branches / curves / warnings
- 输出: BENCHMARK_V23.md
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.lineart.pipeline import LineArtPipeline
from backend.pipeline import CloisonnePipeline
from backend.result_schema import normalize_result, summarize_result

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(BASE, "examples")
FIX = os.path.join(BASE, "tests", "_v23_fixtures")

COLOR_CASES = [
    ("Test01 两色", os.path.join(EX, "test01_two_colors.png"), "cloisonne"),
    ("Test02 三色", os.path.join(EX, "test02_three_colors.png"), "cloisonne"),
    ("Test03 花", os.path.join(EX, "test03_flower.png"), "cloisonne"),
    ("Test04 猫", os.path.join(EX, "test04_cat.png"), "cloisonne"),
]
LINEART_CASES = [
    ("粗直线", os.path.join(FIX, "t1_thick_line.png"), "lineart"),
    ("粗圆环", os.path.join(FIX, "t2_thick_ring.png"), "lineart"),
    ("粗十字", os.path.join(FIX, "t3_thick_cross.png"), "lineart"),
    ("用户线稿", os.path.join(EX, "test_user_lineart.png"), "lineart"),
]

CONFIG_COLOR = {
    "color_precision": 6, "filter_speckle": 4, "mode": "spline", "hierarchical": "cutout",
    "min_region_area_mm2": 1.0, "min_boundary_length_mm": 1.0,
    "simplify_tolerance_mm": 0.15, "wire_diameter_mm": 0.6,
    "min_wire_spacing_mm": 0.8, "min_radius_mm": 1.0, "smoothness": 0.7,
}
CONFIG_LINEART = {
    "binary_threshold": None, "denoise_ksize": 3, "min_spur_length_mm": 0.8,
    "keep_fine_segments": False, "skeleton_method": "skeletonize", "graph_engine": "skan",
    "wire_diameter_mm": 0.6, "recommended_spacing_mm": 0.8,
    "min_radius_mm": 1.0, "simplify_tolerance_mm": 0.15, "smoothness": 0.7,
}


def bench_image(path, mode):
    with open(path, "rb") as f:
        img = f.read()
    if mode == "cloisonne":
        pipe = CloisonnePipeline(dict(CONFIG_COLOR))
    else:
        pipe = LineArtPipeline(dict(CONFIG_LINEART))
    t0 = time.time()
    result = pipe.run(img, output_width_mm=100, img_format="png")
    runtime = time.time() - t0
    n = normalize_result(result)
    s = summarize_result(n)
    img_info = result.get("image_info", {})
    return {
        "image": os.path.basename(path),
        "size_px": f"{img_info.get('width_px')}x{img_info.get('height_px')}",
        "mode": mode,
        "runtime_s": round(runtime, 3),
        "regions": s["regions"], "boundaries": s["boundaries"],
        "branches": s["branches"], "curves": s["curves"],
        "self_intersections": s["self_intersections"],
        "hard_collisions": s["hard_collisions"],
        "dense_warnings": s["dense_warnings"],
        "status": s["status"],
    }


def main():
    print("=" * 96)
    print("Cloisonne2Creo 基准测试 (V2.3 第45阶段)")
    print("=" * 96)
    rows = []
    for name, path, mode in COLOR_CASES + LINEART_CASES:
        if not os.path.exists(path):
            print(f"[SKIP] {name}: {path} 不存在")
            continue
        r = bench_image(path, mode)
        r["name"] = name
        rows.append(r)
        print(f"{name:<12} {r['size_px']:<12} {mode:<9} {r['runtime_s']:<9}"
              f"reg={r['regions']:<4} bnd={r['boundaries']:<4} br={r['branches']:<5} "
              f"cur={r['curves']:<5} selfx={r['self_intersections']:<4} "
              f"hard={r['hard_collisions']:<4} dense={r['dense_warnings']:<5} {r['status']}")

    # 生成 BENCHMARK_V23.md
    md = [
        "# Cloisonne2Creo 基准测试报告 (V2.3)",
        "",
        f"**日期**: 2026-09-04  **版本**: V2.3  **commit**: (V2.3 整合后)",
        "",
        "| 用例 | 图片尺寸(px) | 模式 | runtime(s) | regions | boundaries | branches | curves | 自交 | hard_collision | dense_warning | 状态 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        md.append(f"| {r['name']} | {r['size_px']} | {r['mode']} | {r['runtime_s']} | "
                  f"{r['regions']} | {r['boundaries']} | {r['branches']} | {r['curves']} | "
                  f"{r['self_intersections']} | {r['hard_collisions']} | {r['dense_warnings']} | {r['status']} |")
    md.append("")
    md.append("> 说明: 全部数据来自真实运行 (scripts/benchmark.py), 非人工数据。")
    md_text = "\n".join(md)
    out_md = os.path.join(BASE, "docs", "BENCHMARK_V23.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"\n报告已生成: {out_md}")


if __name__ == "__main__":
    main()
