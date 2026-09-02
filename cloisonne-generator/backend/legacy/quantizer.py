"""
ColorQuantizer - K-Means颜色量化模块
规格书第7章: K-Means Color Quantization, 默认K=8, 允许2~32
规格书第8章: 颜色合并阈值 ΔE=8 (0~30)
"""
import numpy as np
from sklearn.cluster import KMeans


class ColorQuantizer:
    def __init__(self, n_colors=8, merge_delta_e=8.0):
        self.n_colors = max(2, min(32, n_colors))
        self.merge_delta_e = max(0, min(30, merge_delta_e))
        self.kmeans = None
        self.cluster_centers_ = None  # LAB颜色中心
        self.labels_ = None  # 每个像素的标签
        self.color_palette = []  # [{id, lab, rgb, hex, pixel_count, area_ratio}]

    def fit(self, pixels_lab, image_shape):
        """执行K-Means聚类"""
        h, w = image_shape[:2]
        n_samples = min(len(pixels_lab), 200000)  # 采样加速
        if len(pixels_lab) > n_samples:
            idx = np.random.choice(len(pixels_lab), n_samples, replace=False)
            sample = pixels_lab[idx]
        else:
            sample = pixels_lab

        self.kmeans = KMeans(n_clusters=self.n_colors, random_state=42, n_init=3, max_iter=200)
        self.kmeans.fit(sample)
        self.cluster_centers_ = self.kmeans.cluster_centers_

        # 对全图像素预测标签
        self.labels_ = self.kmeans.predict(pixels_lab).reshape(h, w)

        # 合并相似颜色
        if self.merge_delta_e > 0:
            self._merge_similar_colors()

        self._build_palette(pixels_lab)
        return self

    def _merge_similar_colors(self):
        """合并ΔE小于阈值的颜色中心"""
        centers = self.cluster_centers_.copy()
        n = len(centers)
        merged = [False] * n
        mapping = list(range(n))

        for i in range(n):
            if merged[i]:
                continue
            for j in range(i + 1, n):
                if merged[j]:
                    continue
                delta_e = np.sqrt(np.sum((centers[i] - centers[j]) ** 2))
                if delta_e < self.merge_delta_e:
                    # 合并j到i，用像素数加权平均
                    count_i = np.sum(self.labels_ == i)
                    count_j = np.sum(self.labels_ == j)
                    total = count_i + count_j
                    if total > 0:
                        centers[i] = (centers[i] * count_i + centers[j] * count_j) / total
                    self.labels_[self.labels_ == j] = i
                    mapping[j] = i
                    merged[j] = True

        # 重新映射标签为连续ID
        unique_labels = sorted(set(mapping))
        remap = {old: new for new, old in enumerate(unique_labels)}
        new_labels = np.zeros_like(self.labels_)
        for old, new in remap.items():
            new_labels[self.labels_ == old] = new
        self.labels_ = new_labels

        new_centers = np.zeros((len(unique_labels), 3))
        for old, new in remap.items():
            new_centers[new] = centers[old]
        self.cluster_centers_ = new_centers
        self.n_colors = len(unique_labels)

    def _build_palette(self, pixels_lab):
        """构建调色板信息"""
        self.color_palette = []
        total = len(pixels_lab)
        for i in range(self.n_colors):
            lab = self.cluster_centers_[i]
            # LAB -> RGB
            lab_img = lab.reshape(1, 1, 3).astype(np.uint8)
            import cv2
            rgb = cv2.cvtColor(lab_img, cv2.COLOR_LAB2RGB)[0][0]
            hex_color = "#{:02X}{:02X}{:02X}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
            count = int(np.sum(self.labels_ == i))
            self.color_palette.append({
                "id": i,
                "lab": [round(float(x), 2) for x in lab],
                "rgb": [int(x) for x in rgb],
                "hex": hex_color,
                "pixel_count": count,
                "area_ratio": round(count / total, 4) if total > 0 else 0,
            })

    def get_quantized_image(self):
        """返回量化后的RGB图像（用于预览）"""
        import cv2
        h, w = self.labels_.shape
        quantized = np.zeros((h, w, 3), dtype=np.uint8)
        for i in range(self.n_colors):
            lab = self.cluster_centers_[i].reshape(1, 1, 3).astype(np.uint8)
            rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)[0][0]
            quantized[self.labels_ == i] = rgb
        return quantized

    def get_label_map(self):
        return self.labels_
