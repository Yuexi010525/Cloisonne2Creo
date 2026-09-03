# -*- coding: utf-8 -*-
"""生成线稿模式最终曲线叠加原图的对比图, 直观确认无双线"""
import sys, os, cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.lineart.pipeline import LineArtPipeline

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(base, "examples", "test_user_lineart.png")
img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
h, w = img.shape[:2]
_, buf = cv2.imencode(".png", img)

dbg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineart_v21_debug", "t4_user_lineart")
r = LineArtPipeline({"debug_dir": dbg}).run(buf.tobytes())
scale = r["image_info"]["scale_mm_per_px"]

# 叠加图: 白底 + 红色曲线
overlay = np.full((h, w, 3), 255, dtype=np.uint8)
# 先画半透明原图
overlay = cv2.addWeighted(overlay, 0.3, img, 0.7, 0)

curves = r["merged_curves"] if r["merged_curves"] else []
# merged_curves 里只有元数据, 需要从 result["curves"] 或重新获取 segments
# 用 result["curves"] (所有曲线的 segments)
all_curves = r["curves"]
for cid, cdata in all_curves.items():
    for seg in cdata["segments"]:
        pts = []
        for t in np.linspace(0, 1, 30):
            p0 = np.array(seg["p0"]); p1 = np.array(seg["p1"])
            p2 = np.array(seg["p2"]); p3 = np.array(seg["p3"])
            pt = (1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t**2*p2 + t**3*p3
            pts.append(pt)
        for i in range(len(pts)-1):
            x1 = int(pts[i][0] / scale)
            y1 = int(h - pts[i][1] / scale)
            x2 = int(pts[i+1][0] / scale)
            y2 = int(h - pts[i+1][1] / scale)
            cv2.line(overlay, (x1, y1), (x2, y2), (0, 0, 255), 2)

out = os.path.join(dbg, "07_overlay_verify.png")
cv2.imencode(".png", overlay)[1].tofile(out)
print("saved:", out)
print("curves drawn:", len(all_curves))

# 头部区域放大
head = overlay[int(h*0.1):int(h*0.5), int(w*0.2):int(w*0.8)]
head_big = cv2.resize(head, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
out2 = os.path.join(dbg, "08_head_crop_2x.png")
cv2.imencode(".png", head_big)[1].tofile(out2)
print("saved:", out2)
