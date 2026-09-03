# -*- coding: utf-8 -*-
"""
scripts/test_lineart.py - 线稿模式测试工具 (V2.3 第15/44阶段)
- 对粗直线/粗圆环/粗十字/test_user_lineart 运行 LineArtPipeline
- 分别用 graph_engine=skan 和 legacy 对比 (V2.3 第9-10阶段)
- 收集: junction/endpoint/branch/cycle/final_curve/self_intersection/hard_collision/dense_warning/runtime
- 验收: 粗线 → 单中心线 (无两条平行线)
- 输出: GRAPH_AB_REPORT 数据 (stdout, 供报告生成)
"""
import sys, os, time, json
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.lineart.pipeline import LineArtPipeline
from backend.result_schema import normalize_result, summarize_result

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(BASE, "tests", "_v23_fixtures")
USER_LINEART = os.path.join(BASE, "examples", "test_user_lineart.png")

CASES = [
    ("粗直线", os.path.join(FIXTURES, "t1_thick_line.png")),
    ("粗圆环", os.path.join(FIXTURES, "t2_thick_ring.png")),
    ("粗十字", os.path.join(FIXTURES, "t3_thick_cross.png")),
    ("用户线稿", USER_LINEART),
]

CONFIG_BASE = {
    "binary_threshold": None,  # Otsu 自动
    "denoise_ksize": 3,
    "min_spur_length_mm": 0.8,
    "keep_fine_segments": False,
    "skeleton_method": "skeletonize",
    "wire_diameter_mm": 0.6,
    "recommended_spacing_mm": 0.8,
    "min_radius_mm": 1.0,
    "simplify_tolerance_mm": 0.15,
    "smoothness": 0.7,
}


def run_case(path, engine):
    with open(path, "rb") as f:
        img_bytes = f.read()
    config = dict(CONFIG_BASE)
    config["graph_engine"] = engine
    pipe = LineArtPipeline(config)
    t0 = time.time()
    result = pipe.run(img_bytes, output_width_mm=100, img_format="png")
    runtime = time.time() - t0
    n = normalize_result(result)
    s = summarize_result(n)
    s["runtime_s"] = round(runtime, 3)
    # 粗线单中心线检查: final curves 数量应远小于 raw edges
    s["_raw_edges"] = n.get("stats", {}).get("raw_branch_count", s["branches"])
    return s


def main():
    print("=" * 90)
    print("LineArt Skan vs Legacy A/B 测试 (V2.3 第9-10阶段)")
    print("=" * 90)

    rows = []
    for name, path in CASES:
        if not os.path.exists(path):
            print(f"[SKIP] {name}: 文件不存在 {path}")
            continue
        skan = run_case(path, "skan")
        legacy = run_case(path, "legacy")
        rows.append((name, skan, legacy))

    # 输出对比表
    hdr = f"{'指标':<18}{'粗直线(skan/leg)':<24}{'粗圆环(skan/leg)':<24}{'粗十字(skan/leg)':<24}{'用户线稿(skan/leg)':<24}"
    print(hdr)
    print("-" * 90)

    metrics = ["junction_count", "endpoint_count", "branches", "cycle_count",
               "curves", "self_intersections", "hard_collisions", "dense_warnings", "runtime_s"]
    for m in metrics:
        cells = []
        for _, skan, legacy in rows:
            cells.append(f"{skan.get(m, '-'):<8}/{legacy.get(m, '-'):<8}")
        print(f"{m:<18}" + "  ".join(f"{c:<22}" for c in cells))

    # 验收: 粗直线/粗圆环 应产生单中心线
    print("\n--- 验收: 粗线→单中心线 ---")
    for name, skan, legacy in rows:
        if name in ("粗直线", "粗圆环"):
            print(f"{name}: curves skan={skan['curves']}, legacy={legacy['curves']} "
                  f"(期望=1, raw_edges skan={skan['_raw_edges']}/legacy={legacy['_raw_edges']})")

    # 汇总 JSON (供报告)
    out = []
    for name, skan, legacy in rows:
        out.append({"case": name, "skan": skan, "legacy": legacy})
    with open(os.path.join(BASE, "results", "skan_ab_results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: results/skan_ab_results.json")


if __name__ == "__main__":
    main()
