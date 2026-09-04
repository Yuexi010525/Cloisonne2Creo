# -*- coding: utf-8 -*-
"""Optimize BezierFitter:
1) fit(): cap point count (uniform decimation) so a single complex curve
   cannot hang the pipeline on dense boundaries.
2) _point_to_bezier_distance(): vectorize sampling distance (was per-sample
   numpy array allocation, ~20x slower).
"""
p = r'F:\000-deepseek\掐丝模型生成器\cloisonne-generator\backend\curve\bezier_fitter.py'
d = open(p, 'rb').read().decode('utf-8')

# --- 1) add MAX_FIT_POINTS constant after class header ---
old_const = 'class BezierFitter:\n    def __init__(self, max_error_mm=0.1, max_segments=50):'
new_const = ('class BezierFitter:\n'
             '    MAX_FIT_POINTS = 1500  # V2.3.2: 单条曲线拟合点数上限(保护, 避免稠密边界卡死)\n\n'
             '    def __init__(self, max_error_mm=0.1, max_segments=50):')
assert old_const in d, 'const anchor not found'
d = d.replace(old_const, new_const)

# --- 2) fit(): decimate over-long polylines ---
old_fit = '''        pts = np.array(points, dtype=np.float64)
        segments = self._fit_curve(pts, 0, len(pts) - 1)
        return segments'''
new_fit = '''        # V2.3.2: 点数保护, 均匀抽稀保留首尾, 避免复杂边界递归拟合卡死
        if len(points) > self.MAX_FIT_POINTS:
            keep = np.linspace(0, len(points) - 1, self.MAX_FIT_POINTS).astype(int)
            points = [points[i] for i in keep]
        pts = np.array(points, dtype=np.float64)
        segments = self._fit_curve(pts, 0, len(pts) - 1)
        return segments'''
assert old_fit in d, 'fit anchor not found'
d = d.replace(old_fit, new_fit)

# --- 3) vectorize _point_to_bezier_distance ---
old_dist = '''    def _point_to_bezier_distance(self, point, bezier, samples=20):
        """点到贝塞尔曲线的近似距离（采样法）"""
        p = np.array(point, dtype=np.float64)
        min_dist = float('inf')
        for i in range(samples + 1):
            t = i / samples
            bp = self._bezier_point(bezier, t)
            dist = np.linalg.norm(p - bp)
            if dist < min_dist:
                min_dist = dist
        return min_dist'''
new_dist = '''    def _point_to_bezier_distance(self, point, bezier, samples=20):
        """点到贝塞尔曲线的近似距离（采样法, 向量化）"""
        p = np.array(point, dtype=np.float64)
        p0 = np.array(bezier["p0"], dtype=np.float64)
        p1 = np.array(bezier["p1"], dtype=np.float64)
        p2 = np.array(bezier["p2"], dtype=np.float64)
        p3 = np.array(bezier["p3"], dtype=np.float64)
        ts = np.linspace(0.0, 1.0, samples + 1)
        mt = 1.0 - ts
        bps = (mt**3 * p0 + 3 * mt**2 * ts * p1 +
               3 * mt * ts**2 * p2 + ts**3 * p3)
        dists = np.linalg.norm(bps - p, axis=1)
        return float(dists.min())'''
assert old_dist in d, 'dist anchor not found'
d = d.replace(old_dist, new_dist)

open(p, 'wb').write(d.encode('utf-8'))
print('patched bezier_fitter (point cap + vectorized distance)')
