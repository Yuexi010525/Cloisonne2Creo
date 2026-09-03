# -*- coding: utf-8 -*-
"""
scripts/gen_lineart_test_images.py - 生成线稿测试图 (V2.3 第5阶段基线)
- 粗直线 / 粗圆环 / 粗十字 (白底黑粗线)
- 输出到 tests/_v23_fixtures/
"""
import os
import numpy as np
import cv2

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "_v23_fixtures")
os.makedirs(OUT, exist_ok=True)

H, W = 400, 400
LINE_W = 24  # 粗线宽 (px) -> 中心线化后应为 1 条

def save(name, img):
    p = os.path.join(OUT, name)
    # OpenCV imwrite 不支持中文路径, 用 imencode + tofile
    ok, buf = cv2.imencode(".png", img)
    if ok:
        with open(p, "wb") as f:
            f.write(buf.tobytes())
        print(f"生成: {p}")
    else:
        print(f"生成失败: {name}")

def blank():
    return np.full((H, W, 3), 255, dtype=np.uint8)

# 1. 粗直线 (水平, 横跨画面)
img = blank()
cv2.rectangle(img, (60, H // 2 - LINE_W // 2), (W - 60, H // 2 + LINE_W // 2), (0, 0, 0), -1)
save("t1_thick_line.png", img)

# 2. 粗圆环 (中心圆环)
img = blank()
cv2.circle(img, (W // 2, H // 2), 120, (0, 0, 0), LINE_W)
save("t2_thick_ring.png", img)

# 3. 粗十字 (水平+垂直交叉)
img = blank()
cv2.rectangle(img, (60, H // 2 - LINE_W // 2), (W - 60, H // 2 + LINE_W // 2), (0, 0, 0), -1)
cv2.rectangle(img, (W // 2 - LINE_W // 2, 60), (W // 2 + LINE_W // 2, H - 60), (0, 0, 0), -1)
save("t3_thick_cross.png", img)

print("完成")
