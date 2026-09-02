"""
RegionSegmenter - 颜色区域分割模块
规格书第9-11章: 小区域过滤、区域生成、邻接关系
每个区域包含: id, color, area_px, area_mm2, centroid, boundary, neighbors
"""
import numpy as np
import cv2
from scipy import ndimage


class RegionSegmenter:
    def __init__(self, min_region_area_mm2=2.0, scale=1.0):
        self.min_region_area_mm2 = min_region_area_mm2
        self.scale = scale  # mm/px
        self.regions = []
        self.label_map = None  # 连通区域标签图（每个像素属于哪个region id）
        self.color_to_regions = {}  # color_id -> [region_id, ...]

    def segment(self, labels, color_palette):
        """
        从颜色量化标签图分割连通区域
        labels: (H, W) 每个像素的颜色ID
        color_palette: 调色板信息
        """
        h, w = labels.shape
        self.label_map = np.full((h, w), -1, dtype=np.int32)
        self.regions = []
        self.color_to_regions = {}

        region_id = 0
        for color_id in range(len(color_palette)):
            # 生成该颜色的二值mask
            mask = (labels == color_id).astype(np.uint8)
            # 连通区域分析
            num_labels, conn_labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

            for comp_id in range(1, num_labels):  # 跳过背景0
                area_px = int(stats[comp_id, cv2.CC_STAT_AREA])
                area_mm2 = area_px * (self.scale ** 2)

                # 小区域过滤：合并到邻接面积最大的颜色区域
                if area_mm2 < self.min_region_area_mm2:
                    self._merge_small_region(labels, conn_labels, comp_id, color_id)
                    continue

                centroid = centroids[comp_id]
                self.label_map[conn_labels == comp_id] = region_id

                region = {
                    "id": region_id,
                    "color_id": color_id,
                    "color": color_palette[color_id]["hex"],
                    "area_px": area_px,
                    "area_mm2": round(area_mm2, 3),
                    "centroid": [round(float(centroid[0]), 2), round(float(centroid[1]), 2)],
                    "neighbors": set(),
                    "boundary_points": None,
                }
                self.regions.append(region)
                if color_id not in self.color_to_regions:
                    self.color_to_regions[color_id] = []
                self.color_to_regions[color_id].append(region_id)
                region_id += 1

        # 构建邻接关系
        self._build_adjacency()
        return self

    def _merge_small_region(self, labels, conn_labels, comp_id, current_color_id):
        """将小区域合并到邻接面积最大的颜色区域"""
        comp_mask = (conn_labels == comp_id)
        # 膨胀一圈找到邻居
        dilated = cv2.dilate(comp_mask.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1)
        neighbor_pixels = labels[dilated.astype(bool) & ~comp_mask]
        if len(neighbor_pixels) == 0:
            return
        # 找出现次数最多的邻居颜色
        values, counts = np.unique(neighbor_pixels, return_counts=True)
        best_color = values[np.argmax(counts)]
        labels[comp_mask] = best_color

    def _build_adjacency(self):
        """构建区域邻接图（规格书第11章）"""
        h, w = self.label_map.shape
        # 检查每个像素的右方和下方邻居
        for y in range(h):
            for x in range(w - 1):
                a = self.label_map[y, x]
                b = self.label_map[y, x + 1]
                if a >= 0 and b >= 0 and a != b:
                    self.regions[a]["neighbors"].add(b)
                    self.regions[b]["neighbors"].add(a)
            if y < h - 1:
                for x in range(w):
                    a = self.label_map[y, x]
                    b = self.label_map[y + 1, x]
                    if a >= 0 and b >= 0 and a != b:
                        self.regions[a]["neighbors"].add(b)
                        self.regions[b]["neighbors"].add(a)

        # 转换set为list
        for r in self.regions:
            r["neighbors"] = sorted(r["neighbors"])

    def get_regions_info(self):
        return [{k: v for k, v in r.items() if k != "boundary_points"} for r in self.regions]

    def get_region_mask(self, region_id):
        return (self.label_map == region_id).astype(np.uint8)
