# -*- coding: utf-8 -*-
import sys, os, cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.lineart.pipeline import LineArtPipeline

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(base, "examples", "test_user_lineart.png")
img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
_, buf = cv2.imencode(".png", img)
dbg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineart_v21_debug", "t4_user_lineart")
for f in os.listdir(dbg):
    os.remove(os.path.join(dbg, f))
r = LineArtPipeline({"debug_dir": dbg}).run(buf.tobytes())
v = r["validation"]
ls = r["lineart_stats"]
print("graph_engine=%s" % v.get("graph_engine", "?"))
print("branches=%d junctions=%d endpoints=%d cycles=%d pruned=%d" % (
    ls["branch_count"], ls["junction_count"], ls["endpoint_count"],
    ls["cycle_count"], ls["pruned_spurs"]))
print("raw_branches=%d final_curves=%d merged_curves=%d" % (
    ls["raw_branch_count"], ls["final_curve_count"], ls["merged_curve_count"]))
print("hard_collision=%d dense_warning=%d self_intersection=%d status=%s" % (
    v["hard_collision_count"], v["dense_spacing_warning_count"],
    v["self_intersection_count"], v["status"]))
print("debug files:", os.listdir(dbg))
