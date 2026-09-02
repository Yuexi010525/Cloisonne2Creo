"""
CurveMerger - 曲线合并模块
规格书第21-23章:
- G0连续: 终点与下一段起点重合，允许误差0.01mm
- G1连续: 相邻曲线切线方向尽量一致，默认角度误差≤3°
- 曲线合并: 如果G0连续且切线夹角<3°，合并成单条连续Spline
"""
import numpy as np


class CurveMerger:
    def __init__(self, g0_tolerance_mm=0.01, g1_angle_deg=3.0):
        self.g0_tolerance_mm = g0_tolerance_mm
        self.g1_angle_deg = g1_angle_deg

    def check_g0(self, curve_a, curve_b):
        """检查G0连续：曲线A终点 == 曲线B起点（允许误差）"""
        a_end = np.array(curve_a["segments"][-1]["p3"])
        b_start = np.array(curve_b["segments"][0]["p0"])
        d = np.linalg.norm(a_end - b_start)
        return d <= self.g0_tolerance_mm, round(float(d), 6)

    def check_g1(self, curve_a, curve_b):
        """检查G1连续：A终点切线方向与B起点切线方向夹角≤阈值"""
        a_tangent = self._end_tangent(curve_a)
        b_tangent = self._start_tangent(curve_b)
        angle = self._tangent_angle(a_tangent, b_tangent)
        return angle <= self.g1_angle_deg, round(float(angle), 3)

    def _end_tangent(self, curve):
        """曲线终点切线方向"""
        last = curve["segments"][-1]
        p2 = np.array(last["p2"])
        p3 = np.array(last["p3"])
        t = p3 - p2
        n = np.linalg.norm(t)
        return t / n if n > 0 else t

    def _start_tangent(self, curve):
        """曲线起点切线方向"""
        first = curve["segments"][0]
        p0 = np.array(first["p0"])
        p1 = np.array(first["p1"])
        t = p1 - p0
        n = np.linalg.norm(t)
        return t / n if n > 0 else t

    def _tangent_angle(self, t1, t2):
        """两个切线方向的夹角（度）"""
        cos_angle = np.clip(np.dot(t1, t2), -1.0, 1.0)
        angle_rad = np.arccos(cos_angle)
        return abs(np.degrees(angle_rad))

    def merge(self, curves):
        """
        合并连续曲线
        curves: [{"id", "segments": [...]}, ...]
        返回: [{"id", "boundary_ids", "segments", "closed", "type": "merged"}, ...]
        """
        if not curves:
            return []

        # 为每条曲线计算起点和终点
        curve_ends = []
        for c in curves:
            start = np.array(c["segments"][0]["p0"])
            end = np.array(c["segments"][-1]["p3"])
            curve_ends.append({"curve": c, "start": start, "end": end, "used": False})

        merged_groups = []

        # 贪心合并：找与当前组终点最近的未使用曲线
        for i, ce in enumerate(curve_ends):
            if ce["used"]:
                continue
            group = [ce["curve"]]
            ce["used"] = True
            current_end = ce["end"]

            # 不断尝试延伸当前组
            extended = True
            while extended:
                extended = False
                best_idx = None
                best_dist = self.g0_tolerance_mm
                for j, other in enumerate(curve_ends):
                    if other["used"]:
                        continue
                    d = np.linalg.norm(current_end - other["start"])
                    if d <= best_dist:
                        # 检查G1连续性
                        g1_ok, _ = self.check_g1({"segments": self._group_segments(group)}, other["curve"])
                        if g1_ok:
                            best_idx = j
                            best_dist = d

                if best_idx is not None:
                    group.append(curve_ends[best_idx]["curve"])
                    curve_ends[best_idx]["used"] = True
                    current_end = curve_ends[best_idx]["end"]
                    extended = True

            merged_groups.append(group)

        # 生成合并后的曲线
        result = []
        for gi, group in enumerate(merged_groups):
            if not group:
                continue
            all_segments = []
            boundary_ids = []
            for c in group:
                all_segments.extend(c["segments"])
                boundary_ids.append(c["id"])

            # 判断是否闭合
            closed = False
            if len(all_segments) > 1:
                start_pt = np.array(all_segments[0]["p0"])
                end_pt = np.array(all_segments[-1]["p3"])
                if np.linalg.norm(start_pt - end_pt) <= 0.05:  # 0.05mm阈值
                    closed = True

            result.append({
                "id": f"G{gi:03d}",
                "boundary_ids": boundary_ids,
                "segments": all_segments,
                "closed": closed,
                "type": "merged_bezier",
                "segment_count": len(all_segments),
            })

        return result

    def _group_segments(self, group):
        """收集一组曲线的所有段"""
        segments = []
        for c in group:
            segments.extend(c["segments"])
        return segments
