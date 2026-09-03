# -*- coding: utf-8 -*-
"""
LineArtPreprocess - 线稿 BW 二值化预处理
规格书(V2.1线稿模式): 把彩色/灰度线稿统一转为二值黑色Mask(True=前景黑线)。
使用 Otsu 自动阈值 + 可选轻度去噪, 不自己实现阈值算法。
"""
import numpy as np
import cv2


class LineArtPreprocess:
    def __init__(self, config=None):
        self.config = config or {}
        # 二值化阈值: None=Otsu自动, 数值=固定阈值
        self.threshold = self.config.get("binary_threshold", None)
        # 中值滤波去噪核大小(奇数, 0=关闭)
        self.denoise_ksize = self.config.get("denoise_ksize", 3)
        # 形态学闭运算核大小(填充笔画内部小孔, 0=关闭)
        self.close_ksize = self.config.get("close_ksize", 2)

    def to_gray(self, image):
        """输入 BGR/RGB/灰度 → 灰度 uint8"""
        arr = np.asarray(image)
        if arr.ndim == 2:
            return arr.astype(np.uint8)
        if arr.shape[2] == 4:
            arr = arr[..., :3]
        # BGR (OpenCV 习惯)
        return cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)

    def binarize(self, image):
        """
        返回二值Mask: True=前景(黑线), False=背景(白底)
        """
        gray = self.to_gray(image)

        # 轻度去噪
        if self.denoise_ksize and self.denoise_ksize >= 3:
            k = self.denoise_ksize if self.denoise_ksize % 2 == 1 else self.denoise_ksize + 1
            gray = cv2.medianBlur(gray, k)

        # 阈值
        if self.threshold is not None:
            _, binary = cv2.threshold(gray, int(self.threshold), 255, cv2.THRESH_BINARY_INV)
        else:
            # Otsu 自动阈值 + 反色(黑线→白前景)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 形态学闭运算: 填充笔画内部小孔, 让骨架更连续
        if self.close_ksize and self.close_ksize >= 1:
            k = max(1, int(self.close_ksize))
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k * 2 + 1, k * 2 + 1))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # 清除图像边界像素: 很多线稿 PNG 有 1px 深色边框/压缩伪影,
        # 会被二值化成前景, 骨架化后产生横跨画面的异常对角线
        border_crop = self.config.get("border_crop_px", 1)
        if border_crop and border_crop > 0:
            binary[:border_crop, :] = 0
            binary[-border_crop:, :] = 0
            binary[:, :border_crop] = 0
            binary[:, -border_crop:] = 0

        mask = binary > 127
        return mask, gray

    def mask_to_uint8(self, mask):
        """True→255(前景白), False→0(背景黑), 用于可视化"""
        return (mask.astype(np.uint8)) * 255
