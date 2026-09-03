# -*- coding: utf-8 -*-
import sys, os, cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.lineart.pipeline import LineArtPipeline

p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "test_user_lineart.png")
img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
_, buf = cv2.imencode(".png", img)
dbg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineart_v21_debug", "t4_user_lineart")
for f in os.listdir(dbg):
    os.remove(os.path.join(dbg, f))
r = LineArtPipeline({"debug_dir": dbg}).run(buf.tobytes())
v = r["validation"]; ls = r["lineart_stats"]
print("edges=%d nodes=%d pruned=%d" % (ls["skeleton_edges"], ls["skeleton_nodes"], ls["pruned_spurs"]))
print("curves=%d merged=%d" % (ls["curve_count"], ls["merged_curve_count"]))
print("intersections=%d spacing=%d status=%s" % (v["intersection_count"], v["spacing_violation_count"], v["status"]))
print("debug files:", os.listdir(dbg))
