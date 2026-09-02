"""
ImageProcessor - 图片预处理模块
规格书第6章: 缩放 -> 降噪 -> 透明背景处理 -> 颜色空间转换 -> 颜色量化
默认 RGB -> LAB，不要直接在RGB空间做主要颜色聚类。
"""
import cv2
import numpy as np


class ImageProcessor:
    def __init__(self, max_dim=1024):
        self.max_dim = max_dim
        self.original = None
        self.processed = None
        self.lab = None
        self.scale = 1.0
        self.width_px = 0
        self.height_px = 0

    def load(self, image_bytes):
        """从字节加载图片"""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError("无法解码图片，请检查文件格式")
        self.original = img
        return self

    def load_from_array(self, img):
        self.original = img
        return self

    def preprocess(self):
        """完整预处理流程"""
        img = self.original.copy()

        # 透明背景处理：如果有alpha通道，透明区域转为白色
        if img.shape[2] == 4:
            alpha = img[:, :, 3]
            rgb = img[:, :, :3]
            white_bg = np.ones_like(rgb) * 255
            alpha_norm = alpha[:, :, np.newaxis] / 255.0
            rgb = (rgb * alpha_norm + white_bg * (1 - alpha_norm)).astype(np.uint8)
            img = rgb

        # 缩放，保持比例，最长边不超过max_dim
        h, w = img.shape[:2]
        self.width_px, self.height_px = w, h
        if max(w, h) > self.max_dim:
            self.scale = self.max_dim / max(w, h)
            new_w = int(w * self.scale)
            new_h = int(h * self.scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 降噪：双边滤波（保边去噪）
        img = cv2.bilateralFilter(img, d=5, sigmaColor=50, sigmaSpace=50)

        self.processed = img
        # RGB -> LAB (OpenCV用BGR，先转RGB再转LAB)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        return self

    def get_pixels_for_clustering(self):
        """返回用于聚类的LAB像素数组 (N, 3)"""
        h, w = self.lab.shape[:2]
        return self.lab.reshape(-1, 3).astype(np.float32)

    def get_info(self):
        return {
            "width_px": self.width_px,
            "height_px": self.height_px,
            "processed_width": self.processed.shape[1] if self.processed is not None else 0,
            "processed_height": self.processed.shape[0] if self.processed is not None else 0,
            "scale": self.scale,
        }
