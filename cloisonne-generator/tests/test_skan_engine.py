# -*- coding: utf-8 -*-
"""测试 SkanSkeletonGraph"""
import sys, os, cv2, numpy as np, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.lineart.preprocess import LineArtPreprocess
from backend.lineart.skeleton import LineArtSkeleton
from backend.lineart.graph_skan import SkanSkeletonGraph
from backend.lineart.graph import SkeletonGraph as LegacySkeletonGraph

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(base, "examples", "test_user_lineart.png")
img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
h, w = img.shape[:2]
output_width_mm = 100.0
scale = output_width_mm / w

pre = LineArtPreprocess({})
mask, _ = pre.binarize(img)
skel = LineArtSkeleton({}).skeletonize(mask)

print("=== Skan Engine ===")
t0 = time.time()
sg = SkanSkeletonGraph()
sg.extract(skel, spacing_mm_per_px=scale)
t1 = time.time()
print(f"  time: {t1-t0:.2f}s")
print(f"  nodes: {len(sg.nodes)}")
print(f"  edges: {len(sg.edges)}")
print(f"  stats: {sg.stats}")
# 统计 edge 长度分布
lengths = [e["length_px"] for e in sg.edges]
print(f"  edge length: min={min(lengths):.1f} max={max(lengths):.1f} mean={np.mean(lengths):.1f}")
print(f"  closed edges: {sum(1 for e in sg.edges if e.get('closed'))}")

print("\n=== Legacy Engine ===")
t0 = time.time()
lg = LegacySkeletonGraph()
lg.extract(skel)
t1 = time.time()
print(f"  time: {t1-t0:.2f}s")
print(f"  nodes: {len(lg.nodes)}")
print(f"  edges: {len(lg.edges)}")
lengths2 = [e["length_px"] for e in lg.edges]
print(f"  edge length: min={min(lengths2):.1f} max={max(lengths2):.1f} mean={np.mean(lengths2):.1f}")
print(f"  closed edges: {sum(1 for e in lg.edges if e.get('closed'))}")
