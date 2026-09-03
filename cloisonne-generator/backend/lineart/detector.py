# -*- coding: utf-8 -*-
"""
LineArtDetector - 线稿自动检测
规格书(V2.1线稿模式): 通过统计黑色像素比例/白色像素比例/饱和度/唯一颜色数/灰度标准差
判断输入是"黑白线稿"还是"彩色填充图"。
自动检测失败(不确定)时优先进入彩色模式, 而不是错误进入Line Art模式。
"""
import numpy as np


class LineArtDetector:
    def __init__(self, config=None):
        self.config = config or {}
        self.max_unique_colors = self.config.get("detect_max_colors", 12)
        self.max_saturation = self.config.get("detect_max_saturation", 60)
        self.min_white_ratio = self.config.get("detect_min_white", 0.15)
        self.min_ink_ratio = self.config.get("detect_min_ink", 0.02)
        self.bg_threshold = self.config.get("detect_bg_threshold", 235)
        self.ink_threshold = self.config.get("detect_ink_threshold", 90)

    def detect(self, bgr_or_rgb):
        """
        检测输入图片是否为黑白线稿。
        返回: {"mode": "lineart"/"color"/"uncertain", "stats": {...}, "reasons": [...]}
        """
        arr = np.asarray(bgr_or_rgb)
        if arr.ndim == 2:
            gray = arr.astype(np.float32)
            mean_sat = 0.0
        else:
            b = arr[..., 0].astype(np.float32)
            g = arr[..., 1].astype(np.float32)
            r = arr[..., 2].astype(np.float32)
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            mx = np.maximum(np.maximum(b, g), r)
            mn = np.minimum(np.minimum(b, g), r)
            denom = np.maximum(mx, 1e-6)
            sat = np.where(mx > 1e-6, (mx - mn) / denom * 255.0, 0.0)
            mean_sat = float(np.mean(sat))

        bg_ratio = float(np.mean(gray >= self.bg_threshold))
        ink_ratio = float(np.mean(gray <= self.ink_threshold))

        if arr.ndim == 3:
            q = (arr.astype(np.int16) // 32) * 32
            flat = q.reshape(-1, q.shape[-1])
            if flat.shape[0] > 400_000:
                idx = np.linspace(0, flat.shape[0] - 1, 400_000, dtype=np.int64)
                flat = flat[idx]
            unique_colors = len(np.unique(flat, axis=0))
        else:
            unique_colors = len(np.unique((gray // 32).astype(np.uint8)))

        gray_std = float(np.std(gray))

        reasons = []
        is_lineart_candidate = True
        if unique_colors > self.max_unique_colors:
            is_lineart_candidate = False
            reasons.append(f"colors={unique_colors}>{self.max_unique_colors}")
        if arr.ndim == 3 and mean_sat > self.max_saturation:
            is_lineart_candidate = False
            reasons.append(f"sat={mean_sat:.0f}>{self.max_saturation}")
        if bg_ratio < self.min_white_ratio:
            is_lineart_candidate = False
            reasons.append(f"bg={bg_ratio:.2f}<{self.min_white_ratio}")
        if ink_ratio < self.min_ink_ratio:
            is_lineart_candidate = False
            reasons.append(f"ink={ink_ratio:.2f}<{self.min_ink_ratio}")
        if gray_std < 40:
            is_lineart_candidate = False
            reasons.append(f"graystd={gray_std:.0f}<40")

        uncertain = (unique_colors <= self.max_unique_colors + 6
                     and not is_lineart_candidate)

        if is_lineart_candidate:
            mode = "lineart"
        elif uncertain:
            mode = "uncertain"
        else:
            mode = "color"

        return {
            "mode": mode,
            "stats": {
                "unique_colors": int(unique_colors),
                "mean_saturation": round(mean_sat, 1) if arr.ndim == 3 else 0.0,
                "bg_ratio": round(bg_ratio, 3),
                "ink_ratio": round(ink_ratio, 3),
                "gray_std": round(gray_std, 1),
            },
            "reasons": reasons,
        }
