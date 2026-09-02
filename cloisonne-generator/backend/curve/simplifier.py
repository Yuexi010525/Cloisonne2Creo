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
        """对一条折线进行Douglas-Peucker简化"""
        if len(points) <= 2:
            return points
        pts = np.array(points, dtype=np.float64)
        simplified = self._douglas_peucker(pts, 0, len(pts) - 1)
        return [[round(float(x), 4), round(float(y), 4)] for x, y in simplified]

    def _douglas_peucker(self, points, start, end):
        """递归Douglas-Peucker算法"""
        if start >= end:
            return [points[start]]

        # 找距离起点-终点线段最远的点
        max_dist = 0.0
        max_idx = start
        for i in range(start + 1, end):
            dist = self._point_to_line_distance(points[i], points[start], points[end])
            if dist > max_dist:
                max_dist = dist
                max_idx = i

        if max_dist > self.tolerance_mm:
            # 递归处理左右两段
            left = self._douglas_peucker(points, start, max_idx)
            right = self._douglas_peucker(points, max_idx, end)
            # 合并，避免重复中间点
            return left[:-1] + right
        else:
            # 所有点都在容差内，只保留端点
            return [points[start], points[end]]

    def _point_to_line_distance(self, p, line_start, line_end):
        """点到线段的距离"""
        dx = line_end[0] - line_start[0]
        dy = line_end[1] - line_start[1]
        line_len_sq = dx * dx + dy * dy
        if line_len_sq == 0:
            return np.sqrt((p[0] - line_start[0])**2 + (p[1] - line_start[1])**2)
        # 投影参数t
        t = ((p[0] - line_start[0]) * dx + (p[1] - line_start[1]) * dy) / line_len_sq
        t = max(0, min(1, t))
        proj_x = line_start[0] + t * dx
        proj_y = line_start[1] + t * dy
        return np.sqrt((p[0] - proj_x)**2 + (p[1] - proj_y)**2)
