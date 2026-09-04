"""
CurveSimplifier - Douglas-Peucker曲线简化模块
规格书第17章: 默认容差0.15mm，允许0.05~1.0mm
不能直接把几千个像素点全部导入CAD。
"""
import numpy as np


class CurveSimplifier:
    def __init__(self, tolerance_mm=0.15):
        self.tolerance_mm = max(0.05, min(1.0, tolerance_mm))

    def simplify(self, points):
        """对一条折线进行Douglas-Peucker简化
        V2.3.2: 点数保护(>2000 均匀抽稀) + 向量化距离, 防复杂边界卡死"""
        if len(points) <= 2:
            return points
        if len(points) > 2000:
            keep = np.linspace(0, len(points) - 1, 2000).astype(int)
            points = [points[i] for i in keep]
        pts = np.array(points, dtype=np.float64)
        simplified = self._douglas_peucker(pts, 0, len(pts) - 1)
        return [[round(float(x), 4), round(float(y), 4)] for x, y in simplified]

    def _douglas_peucker(self, points, start, end, depth=0):
        """递归Douglas-Peucker算法(向量化距离)"""
        if start >= end:
            return [points[start]]

        a = points[start]
        b = points[end]
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        l2 = dx * dx + dy * dy
        seg = points[start + 1:end]
        if seg.shape[0] == 0:
            return [points[start], points[end]]
        if l2 == 0:
            d = np.sqrt(((seg - a) ** 2).sum(axis=1))
        else:
            t = ((seg[:, 0] - a[0]) * dx + (seg[:, 1] - a[1]) * dy) / l2
            t = np.clip(t, 0.0, 1.0)
            px = a[0] + t * dx
            py = a[1] + t * dy
            d = np.sqrt((seg[:, 0] - px) ** 2 + (seg[:, 1] - py) ** 2)
        max_dist = float(d.max())
        max_idx = int(start + 1 + np.argmax(d))

        if max_dist > self.tolerance_mm and depth < 500:
            left = self._douglas_peucker(points, start, max_idx, depth + 1)
            right = self._douglas_peucker(points, max_idx, end, depth + 1)
            return left[:-1] + right
        else:
            return [points[start], points[end]]
