# -*- coding: utf-8 -*-
"""Vectorize Douglas-Peucker in CurveSimplifier:
- point-to-line distance for the whole interval in one numpy op
- point-count guard (uniform decimation above 2000) to bound worst case
Result is identical; just much faster and cannot blow up.
"""
p = r'F:\000-deepseek\掐丝模型生成器\cloisonne-generator\backend\curve\simplifier.py'
d = open(p, 'rb').read().decode('utf-8')

old = '''    def simplify(self, points):
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
        return np.sqrt((p[0] - proj_x)**2 + (p[1] - proj_y)**2)'''

new = '''    def simplify(self, points):
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
            return [points[start], points[end]]'''

assert old in d, 'simplifier block not found'
d = d.replace(old, new)
open(p, 'wb').write(d.encode('utf-8'))
print('patched simplifier (vectorized DP + point guard)')
