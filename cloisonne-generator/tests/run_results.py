# -*- coding: utf-8 -*-
"""
跑多轮生成结果，供 ChatGPT 评审下一步开发方向
每轮输出 SVG / DXF / IBL / JSON + 预览PNG + 汇总说明
"""
import os
import sys
import json
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline import CloisonnePipeline

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")

ROUNDS = [
    # 名称, 图片, 参数dict
    {
        "name": "R01_test01_基础两色块",
        "image": "test01_two_colors.png",
        "params": dict(color_precision=6, filter_speckle=4, hierarchical="cutout", mode="spline",
                       min_region_area_mm2=1.0, min_boundary_length_mm=1.5,
                       simplify_tolerance_mm=0.15, wire_diameter_mm=0.6,
                       min_wire_spacing_mm=0.8, min_radius_mm=1.0,
                       output_width_mm=100, generate_mode="cloisonne", smoothness=0.7, gen_outline=False),
    },
    {
        "name": "R02_test03_花朵_普通",
        "image": "test03_flower.png",
        "params": dict(color_precision=6, filter_speckle=4, hierarchical="cutout", mode="spline",
                       min_region_area_mm2=1.0, min_boundary_length_mm=1.5,
                       simplify_tolerance_mm=0.15, wire_diameter_mm=0.6,
                       min_wire_spacing_mm=0.8, min_radius_mm=1.0,
                       output_width_mm=100, generate_mode="cloisonne", smoothness=0.7, gen_outline=False),
    },
    {
        "name": "R03_test03_花朵_高精度",
        "image": "test03_flower.png",
        "params": dict(color_precision=12, filter_speckle=2, hierarchical="cutout", mode="spline",
                       min_region_area_mm2=0.5, min_boundary_length_mm=1.0,
                       simplify_tolerance_mm=0.08, wire_diameter_mm=0.6,
                       min_wire_spacing_mm=0.6, min_radius_mm=0.8,
                       output_width_mm=120, generate_mode="cloisonne", smoothness=0.5, gen_outline=True),
    },
    {
        "name": "R04_test03_花朵_快速预览",
        "image": "test03_flower.png",
        "params": dict(color_precision=4, filter_speckle=8, hierarchical="cutout", mode="spline",
                       min_region_area_mm2=4.0, min_boundary_length_mm=2.0,
                       simplify_tolerance_mm=0.25, wire_diameter_mm=0.6,
                       min_wire_spacing_mm=1.0, min_radius_mm=1.2,
                       output_width_mm=100, generate_mode="cloisonne", smoothness=0.3, gen_outline=False),
    },
    {
        "name": "R05_test04_卡通猫_外轮廓",
        "image": "test04_cat.png",
        "params": dict(color_precision=6, filter_speckle=4, hierarchical="cutout", mode="spline",
                       min_region_area_mm2=1.0, min_boundary_length_mm=1.5,
                       simplify_tolerance_mm=0.15, wire_diameter_mm=0.6,
                       min_wire_spacing_mm=0.8, min_radius_mm=1.0,
                       output_width_mm=100, generate_mode="cloisonne", smoothness=0.7, gen_outline=True),
    },
    {
        "name": "R06_test02_三色块_SVG模式",
        "image": "test02_three_colors.png",
        "params": dict(color_precision=6, filter_speckle=4, hierarchical="cutout", mode="spline",
                       min_region_area_mm2=1.0, min_boundary_length_mm=1.0,
                       simplify_tolerance_mm=0.15, wire_diameter_mm=0.6,
                       min_wire_spacing_mm=0.8, min_radius_mm=1.0,
                       output_width_mm=100, generate_mode="svg", smoothness=0.7, gen_outline=False),
    },
]


def run_round(r):
    name = r["name"]
    img_path = os.path.join(EXAMPLES_DIR, r["image"])
    params = r["params"]
    round_dir = os.path.join(RESULTS_DIR, name)
    os.makedirs(round_dir, exist_ok=True)

    pipe = CloisonnePipeline(config=params)
    cfg = {**params, "output_width_mm": params.get("output_width_mm", 100)}
    with open(img_path, "rb") as f:
        image_bytes = f.read()
    t0 = time.time()
    result = pipe.run(image_bytes, output_width_mm=cfg["output_width_mm"], img_format="png")
    elapsed = time.time() - t0

    # 保存JSON
    with open(os.path.join(round_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    # 保存预览SVG（从result里重建）
    preview_svg = result.get("svg", "")
    if preview_svg:
        with open(os.path.join(round_dir, "preview.svg"), "w", encoding="utf-8") as f:
            f.write(preview_svg)

    v = result.get("validation", {})
    summary = {
        "轮次": name,
        "图片": r["image"],
        "耗时秒": round(elapsed, 2),
        "参数": params,
        "区域数": len(result.get("regions", [])),
        "边界数": len(result.get("boundaries", [])),
        "连续曲线组": len(result.get("merged_curves", [])),
        "外轮廓数": v.get("outline_count", 0),
        "检查面板": {
            "短边界": v.get("short_boundary_count", 0),
            "断线": v.get("broken_curve_count", 0),
            "自交": v.get("intersection_count", 0),
            "线距冲突": v.get("spacing_violation_count", 0),
            "小半径": v.get("small_radius_count", 0),
            "状态": v.get("status", ""),
        },
        "文件": {
            "result.json": os.path.exists(os.path.join(round_dir, "result.json")),
            "preview.svg": os.path.exists(os.path.join(round_dir, "preview.svg")),
        },
    }
    return summary


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    summaries = []
    for r in ROUNDS:
        try:
            s = run_round(r)
            summaries.append(s)
            print(f"[OK] {s['轮次']}: 区域={s['区域数']} 边界={s['边界数']} 状态={s['检查面板']['状态']} ({s['耗时秒']}s)")
        except Exception as e:
            print(f"[FAIL] {r['name']}: {e}")
            traceback.print_exc()
            summaries.append({"轮次": r["name"], "错误": str(e)})

    # 汇总文档
    with open(os.path.join(RESULTS_DIR, "RESULTS_SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("# 掐丝珐琅图片转 Creo 曲线生成器 - 多轮生成结果汇总\n\n")
        f.write("生成时间: 自动\n\n")
        f.write("| 轮次 | 图片 | 耗时(s) | 区域 | 边界 | 连续组 | 外轮廓 | 状态 | 短边界 | 断线 | 自交 | 线距冲突 | 小半径 |\n")
        f.write("|------|------|--------|------|------|--------|--------|------|--------|------|------|----------|--------|\n")
        for s in summaries:
            if "错误" in s:
                f.write(f"| {s['轮次']} | - | - | - | - | - | - | FAIL | - | - | - | - | - |\n")
                continue
            c = s["检查面板"]
            f.write(f"| {s['轮次']} | {s['图片']} | {s['耗时秒']} | {s['区域数']} | {s['边界数']} | {s['连续曲线组']} | {s['外轮廓数']} | {c['状态']} | {c['短边界']} | {c['断线']} | {c['自交']} | {c['线距冲突']} | {c['小半径']} |\n")

        f.write("\n## 各轮详细参数\n\n")
        for s in summaries:
            if "错误" in s:
                continue
            f.write(f"### {s['轮次']}\n")
            f.write(f"- 图片: `{s['图片']}`\n")
            f.write(f"- 参数: `{json.dumps(s['参数'], ensure_ascii=False)}`\n")
            f.write(f"- 输出文件: result.json / preview.svg (DXF/IBL在JSON内嵌)\n\n")

    print("\n汇总写入:", os.path.join(RESULTS_DIR, "RESULTS_SUMMARY.md"))


if __name__ == "__main__":
    main()
