"""
SharedBoundaryExtractor - 公共边界提取模块（项目核心）
规格书第12章: 不能分别提取每个Region外轮廓后叠加
必须寻找 Boundary(A) ∩ Boundary(B)，形成 SharedBoundary(A,B)
每条公共边界只保存一次，A-B和B-A认为是同一条边界。
"""
import numpy as np
import cv2
from collections import defaultdict


class SharedBoundaryExtractor:
    def __init__(self, scale=1.0, min_boundary_length_mm=1.5):
        self.scale = scale
        self.min_boundary_length_mm = min_boundary_length_mm
        self.boundaries = []  # [{id, region_a, region_b, points, length_mm, closed}]

    def extract(self, regions, label_map):
        """
        提取所有相邻区域对之间的公共边界
        regions: RegionSegmenter的regions列表
        label_map: (H, W) 区域标签图
        """
        self.boundaries = []
        self.outline_boundaries = []
        h, w = label_map.shape
        boundary_id = 0

        # 收集每对相邻区域的边界像素
        # 用边像素标记：每个边界像素记录它分隔的两个region
        edge_pixels = defaultdict(list)  # (min_r, max_r) -> [(x,y), ...]
        # 外轮廓像素：区域与背景(-1)的边界
        outline_pixels = defaultdict(list)  # region_id -> [(x,y), ...]

        # 水平边
        for y in range(h):
            for x in range(w - 1):
                a = label_map[y, x]
                b = label_map[y, x + 1]
                if a >= 0 and b >= 0 and a != b:
                    key = (min(a, b), max(a, b))
                    edge_pixels[key].append((x + 0.5, y))  # 边中点
                elif a >= 0 and b < 0:
                    outline_pixels[a].append((x + 0.5, y))
                elif b >= 0 and a < 0:
                    outline_pixels[b].append((x + 0.5, y))

        # 垂直边
        for y in range(h - 1):
            for x in range(w):
                a = label_map[y, x]
                b = label_map[y + 1, x]
                if a >= 0 and b >= 0 and a != b:
                    key = (min(a, b), max(a, b))
                    edge_pixels[key].append((x, y + 0.5))
                elif a >= 0 and b < 0:
                    outline_pixels[a].append((x, y + 0.5))
                elif b >= 0 and a < 0:
                    outline_pixels[b].append((x, y + 0.5))

        # 对每对区域，跟踪连续边界曲线
        for (ra, rb), pixels in edge_pixels.items():
            if len(pixels) < 3:
                continue

            # 转换为像素坐标集合，用于边界跟踪
            pixel_set = set()
            for px, py in pixels:
                pixel_set.add((int(round(px)), int(round(py))))

            # 边界跟踪：提取连续曲线段
            curves = self._trace_boundaries(pixel_set)

            for curve_points in curves:
                if len(curve_points) < 3:
                    continue
                # 转换为mm坐标，Y轴翻转（图片Y向下 -> CAD Y向上）
                mm_points = []
                for px, py in curve_points:
                    mm_points.append([
                        round(px * self.scale, 4),
                        round((h - py) * self.scale, 4),
                    ])

                length_mm = self._curve_length(mm_points)
                if length_mm < self.min_boundary_length_mm:
                    continue

                # 判断是否闭合
                closed = False
                if len(mm_points) > 3:
                    d = np.sqrt((mm_points[0][0] - mm_points[-1][0])**2 +
                                (mm_points[0][1] - mm_points[-1][1])**2)
                    if d < 0.05:  # 0.05mm阈值
                        closed = True

                self.boundaries.append({
                    "id": f"B{boundary_id:03d}",
                    "region_a": int(ra),
                    "region_b": int(rb),
                    "points": mm_points,
                    "length_mm": round(length_mm, 3),
                    "closed": closed,
                    "point_count": len(mm_points),
                    "is_outline": False,
                })
                boundary_id += 1

        return self

    def extract_outline(self, regions, label_map):
        """
        提取外轮廓边界（区域与背景的边界），供"生成外轮廓"选项使用
        规格书四十一章: 是否生成外轮廓
        """
        self.outline_boundaries = []
        h, w = label_map.shape
        outline_id = 0

        # 收集区域与背景的边界像素
        outline_pixels = defaultdict(list)
        for y in range(h):
            for x in range(w - 1):
                a = label_map[y, x]
                b = label_map[y, x + 1]
                if a >= 0 and b < 0:
                    outline_pixels[a].append((x + 0.5, y))
                elif b >= 0 and a < 0:
                    outline_pixels[b].append((x + 0.5, y))
        for y in range(h - 1):
            for x in range(w):
                a = label_map[y, x]
                b = label_map[y + 1, x]
                if a >= 0 and b < 0:
                    outline_pixels[a].append((x, y + 0.5))
                elif b >= 0 and a < 0:
                    outline_pixels[b].append((x, y + 0.5))

        # 对每个区域的外轮廓，跟踪连续曲线
        for region_id, pixels in outline_pixels.items():
            if len(pixels) < 3:
                continue
            pixel_set = set()
            for px, py in pixels:
                pixel_set.add((int(round(px)), int(round(py))))

            curves = self._trace_boundaries(pixel_set)
            for curve_points in curves:
                if len(curve_points) < 3:
                    continue
                mm_points = []
                for px, py in curve_points:
                    mm_points.append([
                        round(px * self.scale, 4),
                        round((h - py) * self.scale, 4),
                    ])
                length_mm = self._curve_length(mm_points)
                if length_mm < self.min_boundary_length_mm:
                    continue
                closed = False
                if len(mm_points) > 3:
                    d = np.sqrt((mm_points[0][0] - mm_points[-1][0])**2 +
                                (mm_points[0][1] - mm_points[-1][1])**2)
                    if d < 0.05:
                        closed = True
                self.outline_boundaries.append({
                    "id": f"O{outline_id:03d}",
                    "region_a": int(region_id),
                    "region_b": -1,  # 背景
                    "points": mm_points,
                    "length_mm": round(length_mm, 3),
                    "closed": closed,
                    "point_count": len(mm_points),
                    "is_outline": True,
                })
                outline_id += 1

        return self.outline_boundaries

    def _trace_boundaries(self, pixel_set):
        """从边界像素集合中跟踪连续曲线（8连通）"""
        remaining = set(pixel_set)
        curves = []

        while remaining:
            # 找一个端点（邻居数<=1），如果没有则从任意点开始（闭合曲线）
            start = None
            for p in remaining:
                neighbors = self._count_neighbors(p, remaining)
                if neighbors <= 1:
                    start = p
                    break
            if start is None:
                start = next(iter(remaining))

            # 从start开始跟踪
            curve = [start]
            remaining.remove(start)
            current = start

            while True:
                # 找下一个未访问的邻居
                next_p = None
                for dx, dy in [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]:
                    np_ = (current[0]+dx, current[1]+dy)
                    if np_ in remaining:
                        next_p = np_
                        break
                if next_p is None:
                    break
                curve.append(next_p)
                remaining.remove(next_p)
                current = next_p

            if len(curve) >= 3:
                curves.append(curve)

        return curves

    def _count_neighbors(self, p, pixel_set):
        count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                if (p[0]+dx, p[1]+dy) in pixel_set:
                    count += 1
        return count

    def _curve_length(self, points):
        length = 0.0
        for i in range(len(points) - 1):
            dx = points[i+1][0] - points[i][0]
            dy = points[i+1][1] - points[i][1]
            length += np.sqrt(dx*dx + dy*dy)
        return length

    def get_boundaries_info(self):
        return [{k: v for k, v in b.items() if k != "points"} for b in self.boundaries]
