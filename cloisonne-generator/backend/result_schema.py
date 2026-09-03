# -*- coding: utf-8 -*-
"""
normalize_result - 统一 Result Schema (V2.3 第12-14阶段)
规格书:
  - 目前API返回结果字段来源不够统一 (lineart_stats / validation / strokes / branches ...)
  - 增加 normalize_result(result) 统一内部结构:
    {
      "version": "2.3",
      "mode": "lineart",
      "image": {},
      "geometry": {},
      "stats": {},
      "validation": {},
      "preview": {},
      "exports": {}
    }
  - LineArt geometry: {strokes, branches, centerlines, junctions, endpoints}
  - Color geometry:   {regions, boundaries, curves}
  - 不要让 LineArt 和 Color 继续共享 "boundaries" 这种语义不准确的字段

说明: normalize_result 是"读时映射"工具, 不破坏现有 result 结构,
供服务端基准测试 / 报告 / 前端统一消费使用。
"""
import copy


def normalize_result(raw: dict) -> dict:
    """把 CloisonnePipeline / LineArtPipeline 的结果统一为 V2.3 Schema"""
    if not isinstance(raw, dict):
        return {"version": "2.3", "mode": "unknown", "geometry": {}, "stats": {},
                "validation": {}, "preview": {}, "exports": {}, "image": {}}

    mode = raw.get("mode") or raw.get("engine") or "unknown"

    # ---- image ----
    image = dict(raw.get("image_info") or {})
    image["width_px"] = raw.get("image_info", {}).get("width_px")
    image["height_px"] = raw.get("image_info", {}).get("height_px")

    # ---- geometry (按 mode 语义分组) ----
    geometry = {}
    if mode == "lineart":
        geometry = {
            "strokes": raw.get("strokes", []),
            "branches": raw.get("branches", []),
            "centerlines": raw.get("centerlines", {}),
            "junctions": raw.get("junctions", []),
            "endpoints": raw.get("endpoints", []),
        }
    elif mode in ("cloisonne", "color", "spline"):
        geometry = {
            "regions": raw.get("regions", []),
            "boundaries": raw.get("boundaries", []),
            "curves": raw.get("curves", {}),
        }
    else:
        # svg / outline / 未知: 尽量保留
        for k in ("regions", "boundaries", "curves", "strokes", "branches",
                  "centerlines", "junctions", "endpoints"):
            if k in raw:
                geometry[k] = raw.get(k)

    # ---- stats ----
    stats = dict(raw.get("lineart_stats") or raw.get("stats") or {})
    # 合并曲线统计（彩色模式）
    if "curves_summary" in raw:
        stats["curve_count"] = len(raw.get("curves_summary", {}))
    if "merged_curves" in raw and isinstance(raw.get("merged_curves"), list):
        stats["merged_curve_count"] = len(raw.get("merged_curves", []))
    if "curves" in raw and isinstance(raw.get("curves"), dict):
        stats["curve_count"] = len(raw.get("curves", {}))

    # ---- validation ----
    validation = dict(raw.get("validation") or {})

    # ---- preview ----
    preview = dict(raw.get("preview_images") or {})
    preview["svg"] = raw.get("svg")

    # ---- exports ----
    exports = {
        "dxf_base64": raw.get("dxf_base64"),
        "ibl_text": raw.get("ibl_text"),
    }

    return {
        "version": "2.3",
        "mode": mode,
        "engine": raw.get("engine"),
        "graph_engine": raw.get("graph_engine"),
        "image": image,
        "geometry": geometry,
        "stats": stats,
        "validation": validation,
        "preview": preview,
        "exports": exports,
    }


def summarize_result(normalized: dict) -> dict:
    """从 normalized result 提取用于报告/基准的指标摘要"""
    stats = normalized.get("stats", {})
    validation = normalized.get("validation", {})
    geometry = normalized.get("geometry", {})
    mode = normalized.get("mode")

    summary = {
        "mode": mode,
        "regions": len(geometry.get("regions", [])),
        "boundaries": len(geometry.get("boundaries", [])),
        "strokes": len(geometry.get("strokes", [])),
        "branches": len(geometry.get("branches", [])),
        "junction_count": stats.get("junction_count", len(geometry.get("junctions", []))),
        "endpoint_count": stats.get("endpoint_count", len(geometry.get("endpoints", []))),
        "junctions": stats.get("junction_count", len(geometry.get("junctions", []))),
        "endpoints": stats.get("endpoint_count", len(geometry.get("endpoints", []))),
        "cycle_count": stats.get("cycle_count", 0),
        "curves": stats.get("final_curve_count",
                            stats.get("curve_count",
                                      len(geometry.get("curves", {})))),
        "merged_curves": stats.get("merged_curve_count",
                                   validation.get("merged_curve_count", 0)),
        "self_intersections": validation.get("self_intersection_count",
                                             validation.get("intersection_count", 0)),
        "hard_collisions": validation.get("hard_collision_count", 0),
        "dense_warnings": validation.get("dense_spacing_warning_count", 0),
        "status": validation.get("status"),
        "runtime_s": raw_runtime(normalized),
    }
    return summary


def raw_runtime(normalized: dict) -> float:
    """从 normalized 提取 runtime（若有）"""
    val = normalized.get("validation", {})
    if isinstance(val, dict):
        return val.get("runtime_s", 0.0)
    return 0.0
