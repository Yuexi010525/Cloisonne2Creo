# -*- coding: utf-8 -*-
"""规格书第60章测试案例：生成Test01-04测试图片"""
import numpy as np
import cv2
import os

os.makedirs("examples", exist_ok=True)

# Test 01: 两色块，预期1条公共边界
# AAAAAA|BBBBBB
# AAAAAA|BBBBBB
h, w = 200, 300
img = np.zeros((h, w, 3), dtype=np.uint8)
img[:, :w//2] = [0, 0, 255]   # 红 A
img[:, w//2:] = [255, 0, 0]   # 蓝 B
cv2.imwrite("examples/test01_two_colors.png", img)
print("Test01 两色块:", img.shape)

# Test 02: 三色块，预期A-B, A-C, B-C
# AAAAAAAA
# AABBBBBB
# AACCCCCC
h, w = 240, 240
img = np.zeros((h, w, 3), dtype=np.uint8)
img[:h//3, :] = [0, 0, 255]       # A 红 上
img[h//3:2*h//3, :w//2] = [0, 255, 0]   # B 绿 中左
img[h//3:2*h//3, w//2:] = [0, 255, 255] # C 黄 中右
img[2*h//3:, :] = [255, 0, 0]     # 下边 蓝
cv2.imwrite("examples/test02_three_colors.png", img)
print("Test02 三色块:", img.shape)

# Test 03: 复杂花朵（多层圆形花瓣，检查曲线连续性/最小半径/线距）
h, w = 400, 400
img = np.ones((h, w, 3), dtype=np.uint8) * 255
# 背景浅灰
img[:] = [220, 220, 220]
# 花心（深黄）
cv2.circle(img, (200, 200), 40, (0, 128, 255), -1)
# 花瓣（红，8片）
import math
for i in range(8):
    angle = i * math.pi / 4
    cx = 200 + int(95 * math.cos(angle))
    cy = 200 + int(95 * math.sin(angle))
    cv2.circle(img, (cx, cy), 35, (0, 0, 255), -1)
# 花茎（绿）
cv2.rectangle(img, (195, 250), (205, 380), (0, 200, 0), -1)
# 叶片（深绿）
cv2.ellipse(img, (170, 330), (50, 20), -30, 0, 360, (0, 150, 0), -1)
cv2.ellipse(img, (230, 350), (45, 18), 30, 0, 360, (0, 150, 0), -1)
cv2.imwrite("examples/test03_flower.png", img)
print("Test03 花朵:", img.shape)

# Test 04: 卡通动物（简单猫头，检查小区域/眼睛/花纹/内部细节）
h, w = 360, 360
img = np.ones((h, w, 3), dtype=np.uint8) * 255
img[:] = [240, 240, 240]
# 脸（浅橙）
cv2.circle(img, (180, 180), 120, (0, 140, 255), -1)
# 耳朵（深棕）
cv2.circle(img, (110, 90), 50, (0, 90, 160), -1)
cv2.circle(img, (250, 90), 50, (0, 90, 160), -1)
# 眼睛（白底）
cv2.circle(img, (145, 160), 25, (255, 255, 255), -1)
cv2.circle(img, (215, 160), 25, (255, 255, 255), -1)
# 瞳孔（黑）
cv2.circle(img, (148, 162), 10, (0, 0, 0), -1)
cv2.circle(img, (212, 162), 10, (0, 0, 0), -1)
# 鼻子（粉）
cv2.circle(img, (180, 210), 12, (200, 100, 255), -1)
# 嘴（深红）
cv2.ellipse(img, (180, 235), (30, 18), 0, 0, 180, (0, 0, 200), 3)
# 胡须（深棕线）
cv2.line(img, (120, 195), (60, 185), (0, 90, 160), 3)
cv2.line(img, (120, 210), (55, 215), (0, 90, 160), 3)
cv2.line(img, (240, 195), (300, 185), (0, 90, 160), 3)
cv2.line(img, (240, 210), (305, 215), (0, 90, 160), 3)
cv2.imwrite("examples/test04_cat.png", img)
print("Test04 卡通猫:", img.shape)

print("\n4张测试图已生成到 examples/")
