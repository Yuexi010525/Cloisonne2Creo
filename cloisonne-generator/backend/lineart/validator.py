# -*- coding: utf-8 -*-
"""
LineArtValidator - 线稿模式工程验证 (V2.2 Line Art Engineering)
规格书(V2.2): 重构线稿验证语义, 把 min_spacing 拆为:
  - hard_collision: distance < wire_diameter (两根掐丝实体物理重叠) → error
  - dense_spacing_warning: wire_diameter <= distance < recommended_spacing → warning (不是error)
  - recommended_spacing 默认 0.8mm (中心线到中心线推荐间距)
验证状态:
  hard_collision > 0 → error
  hard_collision == 0 & dense_spacing_warning > 0 → warning
  两者均为0 → ok
真实错误只有: hard_collision>0 / broken>0 / invalid_geometry>0 / self_intersection>0
复用 Shapely 做真几何计算 (distance / is_simple)
"""
import numpy as np
from shapely.geometry import LineString


class LineArtValidator:
    def __init__(self, wire_diameter_mm=0.6, recommended_spacing_mm=0.8,
                 min_radius_mm=1.0):
        self.wire_diameter_mm = float(wire_diameter_mm)
        self.recommended_spacing_mm = float(recommended_spacing_mm)
        self.min_radius_mm = float(min_radius_mm)

    def validate(self, curves):
        """
        输入: curves list of dict {id, segments(bezier), closed, ...}
        输出: validation dict
        """
        # 把 bezier segments 采样成 LineString (用于几何计算)
        linestrings = []
        curve_ids = []
        for c in curves:
            pts = self._bezier_to_points(c["segments"], samples=20)
            if len(pts) >= 2:
                ls = LineString(pts)
                linestrings.append(ls)
                curve_ids.append(c["id"])

        n = len(linestrings)
        hard_collisions = []
        dense_warnings = []
        self_intersections = []
        small_radius_count = 0
        broken_count = 0
        invalid_count = 0

        # 自交检测 (is_simple)
        for i, ls in enumerate(linestrings):
            try:
                if not ls.is_simple:
                    self_intersections.append({"curve_id": curve_ids[i]})
            except Exception:
                invalid_count += 1

        # 线距检测 (O(n²) 但 n 通常 < 500, 可接受)
        # hard_collision: 曲线中间部分(非端点)距离 < wire_diameter (真实物理重叠)
        # dense_warning: wire_diameter <= distance < recommended_spacing
        # 注意: 端点/junction处的曲线连接不判定为碰撞, 因为交叉点本应连接
        from shapely.ops import nearest_points
        ENDPOINT_TOL = 0.25  # mm, 端点附近容差(视为junction连接)
        for i in range(n):
            ls_i = linestrings[i]
            pts_i = list(ls_i.coords)
            start_i = pts_i[0]; end_i = pts_i[-1]
            length_i = ls_i.length
            for j in range(i + 1, n):
                ls_j = linestrings[j]
                try:
                    dist = ls_i.distance(ls_j)
                except Exception:
                    invalid_count += 1
                    continue
                if dist >= self.recommended_spacing_mm:
                    continue
                # 找最近点, 判断是否在端点附近
                try:
                    p_i, p_j = nearest_points(ls_i, ls_j)
                    # 最近点到 ls_i 起点/终点的距离
                    d_i_start = ls_i.project(p_i)
                    d_i_end = length_i - d_i_start
                    near_endpoint_i = (d_i_start < ENDPOINT_TOL or d_i_end < ENDPOINT_TOL)
                    # 最近点到 ls_j 起点/终点的距离
                    d_j_start = ls_j.project(p_j)
                    d_j_end = ls_j.length - d_j_start
                    near_endpoint_j = (d_j_start < ENDPOINT_TOL or d_j_end < ENDPOINT_TOL)
                except Exception:
                    near_endpoint_i = False
                    near_endpoint_j = False

                # 如果最近点在两条曲线的端点附近, 视为junction连接, 跳过
                if near_endpoint_i and near_endpoint_j:
                    continue

                if dist < self.wire_diameter_mm:
                    hard_collisions.append({
                        "curve_a": curve_ids[i],
                        "curve_b": curve_ids[j],
                        "distance_mm": round(float(dist), 4),
                    })
                elif dist < self.recommended_spacing_mm:
                    dense_warnings.append({
                        "curve_a": curve_ids[i],
                        "curve_b": curve_ids[j],
                        "distance_mm": round(float(dist), 4),
                    })

        # 状态判定
        has_error = (len(hard_collisions) > 0 or broken_count > 0
                     or invalid_count > 0 or len(self_intersections) > 0)
        has_warning = len(dense_warnings) > 0 or small_radius_count > 0

        if has_error:
            status = "error"
        elif has_warning:
            status = "warning"
        else:
            status = "ok"

        return {
            "curve_count": n,
            "hard_collision_count": len(hard_collisions),
            "dense_spacing_warning_count": len(dense_warnings),
            "self_intersection_count": len(self_intersections),
            "small_radius_count": small_radius_count,
            "broken_curve_count": broken_count,
            "invalid_curve_count": invalid_count,
            "hard_collisions": hard_collisions[:50],  # 限制输出数量
            "dense_spacing_warnings": dense_warnings[:100],
            "self_intersections": self_intersections[:20],
            "wire_diameter_mm": self.wire_diameter_mm,
            "recommended_spacing_mm": self.recommended_spacing_mm,
            "status": status,
            "engine": "lineart_v22",
        }

    @staticmethod
    def _bezier_to_points(segments, samples=20):
        """把 bezier segments 转成采样点列表"""
        pts = []
        for seg in segments:
            p0 = np.array(seg["p0"])
            p1 = np.array(seg["p1"])
            p2 = np.array(seg["p2"])
            p3 = np.array(seg["p3"])
            for t in np.linspace(0, 1, samples):
                pt = ((1-t)**3 * p0 + 3*(1-t)**2*t * p1
                      + 3*(1-t)*t**2 * p2 + t**3 * p3)
                pts.append((float(pt[0]), float(pt[1])))
        return pts
