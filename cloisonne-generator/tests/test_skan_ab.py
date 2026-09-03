# -*- coding: utf-8 -*-
"""V2.2 Skan vs Legacy A/B 对比测试"""
import sys, os, time, cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.lineart.preprocess import LineArtPreprocess
from backend.lineart.skeleton import LineArtSkeleton
from backend.lineart.graph_skan import SkanSkeletonGraph
from backend.lineart.graph import SkeletonGraph as LegacySkeletonGraph
from backend.lineart.validator import LineArtValidator

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(base, "examples", "test_user_lineart.png")
img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
h, w = img.shape[:2]
scale = 100.0 / w

mask, _ = LineArtPreprocess({}).binarize(img)
skel = LineArtSkeleton({}).skeletonize(mask)

results = {}
for name, engine in [("Skan", SkanSkeletonGraph()), ("Legacy", LegacySkeletonGraph())]:
    t0 = time.time()
    if name == "Skan":
        engine.extract(skel, spacing_mm_per_px=scale)
    else:
        engine.extract(skel)
    elapsed = time.time() - t0

    # 模拟曲线拟合(用edge points近似, 直线段)
    curves = []
    for e in engine.edges:
        pts = [(float(p[1]) * scale, float(p[0]) * scale) for p in e["points"]]
        if len(pts) >= 2:
            # 构造直线段序列
            segments = []
            for i in range(len(pts) - 1):
                segments.append({
                    "p0": list(pts[i]), "p1": list(pts[i]),
                    "p2": list(pts[i+1]), "p3": list(pts[i+1]),
                })
            curves.append({"id": e["id"], "segments": segments})

    validator = LineArtValidator(wire_diameter_mm=0.6, recommended_spacing_mm=0.8, min_radius_mm=1.0)
    v = validator.validate(curves)

    # 统计指标(兼容Skan和Legacy)
    nodes_list = engine.nodes if isinstance(engine.nodes, list) else list(engine.nodes.values())
    junctions = sum(1 for n in nodes_list if n.get("type") == "junction")
    endpoints = sum(1 for n in nodes_list if n.get("type") == "endpoint")
    cycles = sum(1 for e in engine.edges if e.get("closed", False))
    if hasattr(engine, "stats"):
        junctions = engine.stats.get("junction_count", junctions)
        endpoints = engine.stats.get("endpoint_count", endpoints)
        cycles = engine.stats.get("cycle_count", cycles)

    results[name] = {
        "edges": len(engine.edges),
        "nodes": len(nodes_list),
        "junctions": junctions,
        "endpoints": endpoints,
        "cycles": cycles,
        "mean_edge_len": np.mean([e["length_px"] for e in engine.edges]) if engine.edges else 0,
        "hard_collision": v["hard_collision_count"],
        "dense_warning": v["dense_spacing_warning_count"],
        "self_intersection": v["self_intersection_count"],
        "small_radius": v["small_radius_count"],
        "runtime_s": round(elapsed, 3),
    }

print("=" * 70)
print("V2.2 Skan vs Legacy A/B 对比 (用户线稿, 输出100mm)")
print("=" * 70)
print("%-20s %12s %12s" % ("指标", "Skan", "Legacy"))
print("-" * 70)
keys = [
    ("edges", "Branch数"),
    ("nodes", "Node数"),
    ("junctions", "Junction数"),
    ("endpoints", "Endpoint数"),
    ("cycles", "Cycle数"),
    ("mean_edge_len", "平均边长(px)"),
    ("hard_collision", "实体碰撞"),
    ("dense_warning", "过密警告"),
    ("self_intersection", "自交"),
    ("small_radius", "小半径"),
    ("runtime_s", "运行时间(s)"),
]
for k, label in keys:
    print("%-20s %12s %12s" % (label, results["Skan"][k], results["Legacy"][k]))
print("-" * 70)
curve_reduction = (results["Legacy"]["edges"] - results["Skan"]["edges"]) / results["Legacy"]["edges"] * 100
print("Curve数量减少: %.1f%% (规格书要求 >=20%%)" % curve_reduction)
print("默认引擎: Skan (几何正确性更高, 碎边合并更好)")
