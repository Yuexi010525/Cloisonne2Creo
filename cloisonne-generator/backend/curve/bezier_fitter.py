"""
BezierFitter - 三次贝塞尔曲线拟合模块
规格书第18章: 优先Cubic Bezier / Cubic B-Spline
禁止输出大量LINE，必须尽量生成Spline
规格书第19章: 统一内部数据结构 {type, p0, p1, p2, p3}
"""
import numpy as np


class BezierFitter:
    def __init__(self, max_error_mm=0.1, max_segments=50):
        self.max_error_mm = max_error_mm
        self.max_segments = max_segments

    def fit(self, points):
        """
        将折线拟合为分段三次贝塞尔曲线
        返回: [{type: "cubic_bezier", p0, p1, p2, p3}, ...]
        """
        if len(points) < 2:
            return []
        if len(points) == 2:
            # 两点退化为直线（用贝塞尔表示）
            p0, p3 = points[0], points[1]
            p1 = [p0[0] + (p3[0]-p0[0])/3, p0[1] + (p3[1]-p0[1])/3]
            p2 = [p0[0] + 2*(p3[0]-p0[0])/3, p0[1] + 2*(p3[1]-p0[1])/3]
            return [{"type": "cubic_bezier", "p0": p0, "p1": p1, "p2": p2, "p3": p3}]

        pts = np.array(points, dtype=np.float64)
        segments = self._fit_curve(pts, 0, len(pts) - 1)
        return segments

    def _fit_curve(self, points, start, end, depth=0):
        """递归拟合：如果误差超过阈值，则在最大误差点拆分"""
        if depth > 20 or (end - start) < 2:
            return [self._fit_single_segment(points[start:end+1])]

        segment = self._fit_single_segment(points[start:end+1])

        # 计算最大误差
        max_error = 0.0
        max_idx = start
        for i in range(start + 1, end):
            # 计算点到贝塞尔曲线的近似距离（采样比较）
            dist = self._point_to_bezier_distance(points[i], segment)
            if dist > max_error:
                max_error = dist
                max_idx = i

        if max_error > self.max_error_mm and (max_idx - start) > 1 and (end - max_idx) > 1:
            left = self._fit_curve(points, start, max_idx, depth + 1)
            right = self._fit_curve(points, max_idx, end, depth + 1)
            return left + right
        else:
            return [segment]

    def _fit_single_segment(self, points):
        """
        用端点切线法拟合单段三次贝塞尔
        适用于点列比较平滑的情况
        """
        pts = np.array(points, dtype=np.float64)
        n = len(pts)
        p0 = pts[0]
        p3 = pts[-1]

        if n < 3:
            p1 = p0 + (p3 - p0) / 3
            p2 = p0 + 2 * (p3 - p0) / 3
        else:
            # 用弦长参数化
            chords = np.zeros(n)
            for i in range(1, n):
                chords[i] = chords[i-1] + np.linalg.norm(pts[i] - pts[i-1])
            total = chords[-1] if chords[-1] > 0 else 1
            t = chords / total

            # 端点切线：用前几个点和后几个点的方向
            tangent_start = pts[min(2, n-1)] - pts[0]
            tangent_end = pts[-1] - pts[max(-3, -n)]
            norm_start = np.linalg.norm(tangent_start)
            norm_end = np.linalg.norm(tangent_end)
            if norm_start > 0:
                tangent_start = tangent_start / norm_start
            if norm_end > 0:
                tangent_end = tangent_end / norm_end

            # 控制点距离端点的距离（经验值：弦长的1/3）
            chord_len = np.linalg.norm(p3 - p0)
            handle_len = chord_len / 3.0
            p1 = p0 + tangent_start * handle_len
            p2 = p3 - tangent_end * handle_len

        return {
            "type": "cubic_bezier",
            "p0": [round(float(p0[0]), 4), round(float(p0[1]), 4)],
            "p1": [round(float(p1[0]), 4), round(float(p1[1]), 4)],
            "p2": [round(float(p2[0]), 4), round(float(p2[1]), 4)],
            "p3": [round(float(p3[0]), 4), round(float(p3[1]), 4)],
        }

    def _point_to_bezier_distance(self, point, bezier, samples=20):
        """点到贝塞尔曲线的近似距离（采样法）"""
        p = np.array(point, dtype=np.float64)
        min_dist = float('inf')
        for i in range(samples + 1):
            t = i / samples
            bp = self._bezier_point(bezier, t)
            dist = np.linalg.norm(p - bp)
            if dist < min_dist:
                min_dist = dist
        return min_dist

    def _bezier_point(self, bezier, t):
        """计算贝塞尔曲线上t处的点"""
        p0 = np.array(bezier["p0"], dtype=np.float64)
        p1 = np.array(bezier["p1"], dtype=np.float64)
        p2 = np.array(bezier["p2"], dtype=np.float64)
        p3 = np.array(bezier["p3"], dtype=np.float64)
        mt = 1 - t
        return (mt**3 * p0 + 3 * mt**2 * t * p1 +
                3 * mt * t**2 * p2 + t**3 * p3)

    def to_svg_path(self, segments):
        """将贝塞尔段列表转换为SVG path d属性字符串"""
        if not segments:
            return ""
        parts = [f"M {segments[0]['p0'][0]} {segments[0]['p0'][1]}"]
        for seg in segments:
            parts.append(f"C {seg['p1'][0]} {seg['p1'][1]}, "
                        f"{seg['p2'][0]} {seg['p2'][1]}, "
                        f"{seg['p3'][0]} {seg['p3'][1]}")
        return " ".join(parts)
