"""
CurveMerger - 曲线合并模块
规格书第21-23章 + V2.1 (ChatGPT审查意见):
- G0连续: 终点与下一段起点重合，允许误差0.01mm
- G1连续: 相邻曲线切线方向夹角 ≤ 3°
- V2.1: 支持4种端点组合 + 自动翻转方向:
  A.end→B.start / A.end→B.end / A.start→B.start / A.start→B.end
  必要时 reverse(B) 后再判断 G0/G1
"""
import numpy as np


class CurveMerger:
    def __init__(self, g0_tolerance_mm=0.01, g1_angle_deg=3.0):
        self.g0_tolerance_mm = g0_tolerance_mm
        self.g1_angle_deg = g1_angle_deg

    # =====================================================================
    # 切线工具（基于段序列）
    # =====================================================================
    @staticmethod
    def _seg_start_tangent(seg):
        p0 = np.array(seg["p0"])
        p1 = np.array(seg["p1"])
        t = p1 - p0
        n = np.linalg.norm(t)
        return t / n if n > 0 else t

    @staticmethod
    def _seg_end_tangent(seg):
        p2 = np.array(seg["p2"])
        p3 = np.array(seg["p3"])
        t = p3 - p2
        n = np.linalg.norm(t)
        return t / n if n > 0 else t

    @classmethod
    def _seq_start_tangent(cls, segments):
        return cls._seg_start_tangent(segments[0])

    @classmethod
    def _seq_end_tangent(cls, segments):
        return cls._seg_end_tangent(segments[-1])

    @staticmethod
    def _tangent_angle(t1, t2):
        cos_angle = np.clip(np.dot(t1, t2), -1.0, 1.0)
        return abs(np.degrees(np.arccos(cos_angle)))

    @staticmethod
    def _reverse_segments(segments):
        """翻转段序列方向（段序反转 + 每段起终点互换）"""
        new = []
        for seg in reversed(segments):
            new.append({
                "p0": seg["p3"], "p1": seg["p2"],
                "p2": seg["p1"], "p3": seg["p0"],
            })
        return new

    # =====================================================================
    # 兼容旧接口
    # =====================================================================
    def check_g0(self, curve_a, curve_b):
        a_end = np.array(curve_a["segments"][-1]["p3"])
        b_start = np.array(curve_b["segments"][0]["p0"])
        d = np.linalg.norm(a_end - b_start)
        return d <= self.g0_tolerance_mm, round(float(d), 6)

    def check_g1(self, curve_a, curve_b):
        a_tangent = self._seq_end_tangent(curve_a["segments"])
        b_tangent = self._seq_start_tangent(curve_b["segments"])
        angle = self._tangent_angle(a_tangent, b_tangent)
        return angle <= self.g1_angle_deg, round(float(angle), 3)

    # =====================================================================
    # V2.1 合并（4种端点组合 + 自动翻转）
    # =====================================================================
    def merge(self, curves):
        """
        合并连续曲线（V2.1: 支持自动翻转方向）
        curves: [{"id", "segments": [...]}, ...]
        返回: [{"id", "boundary_ids", "segments", "closed", "type": "merged"}, ...]
        """
        if not curves:
            return []

        # 预计算每条曲线的 segments（可能是空）
        items = []
        for c in curves:
            segs = c.get("segments") or []
            if not segs:
                continue
            items.append({
                "id": c["id"],
                "normal": segs,
                "flipped": self._reverse_segments(segs),
                "used": False,
            })

        merged_groups = []  # 每个是 (segments列表, boundary_ids列表)

        for idx, item in enumerate(items):
            if item["used"]:
                continue
            group_segs = list(item["normal"])
            group_ids = [item["id"]]
            item["used"] = True

            extended = True
            while extended:
                extended = False
                best_action = None  # (mode, other_item, use_flip, dist)
                best_dist = self.g0_tolerance_mm

                cur_start = self._first_pt(group_segs)
                cur_end = self._last_pt(group_segs)
                cur_start_tangent = self._seq_start_tangent(group_segs)
                cur_end_tangent = self._seq_end_tangent(group_segs)

                for other in items:
                    if other["used"]:
                        continue
                    normal = other["normal"]
                    flipped = other["flipped"]
                    n_start = self._first_pt(normal)
                    n_end = self._last_pt(normal)
                    n_start_tan = self._seq_start_tangent(normal)
                    n_end_tan = self._seq_end_tangent(normal)
                    # flipped 的 start/end 切线 = 原 end/start 的反向
                    f_start_tan = -n_end_tan
                    f_end_tan = -n_start_tan

                    # 4种连接方式
                    candidates = []
                    # 1. append normal: group.end → other.start
                    d = np.linalg.norm(cur_end - n_start)
                    if d <= best_dist and self._g1_ok(cur_end_tangent, n_start_tan):
                        candidates.append(("append", other, False, d))
                    # 2. append flipped: group.end → other.end
                    d = np.linalg.norm(cur_end - n_end)
                    if d <= best_dist and self._g1_ok(cur_end_tangent, f_start_tan):
                        candidates.append(("append", other, True, d))
                    # 3. prepend normal: other.end → group.start
                    d = np.linalg.norm(n_end - cur_start)
                    if d <= best_dist and self._g1_ok(n_end_tan, cur_start_tangent):
                        candidates.append(("prepend", other, False, d))
                    # 4. prepend flipped: flipped.end(原start) → group.start
                    d = np.linalg.norm(n_start - cur_start)
                    if d <= best_dist and self._g1_ok(f_end_tan, cur_start_tangent):
                        candidates.append(("prepend", other, True, d))

                    for cand in candidates:
                        if cand[3] < best_dist or (
                                cand[3] <= best_dist and best_action is None):
                            best_action = cand
                            best_dist = cand[3]

                if best_action is not None:
                    mode, other, use_flip, dist = best_action
                    segs = other["flipped"] if use_flip else other["normal"]
                    if mode == "append":
                        group_segs.extend(segs)
                        group_ids.append(other["id"])
                    else:  # prepend
                        group_segs = segs + group_segs
                        group_ids.insert(0, other["id"])
                    other["used"] = True
                    extended = True

            merged_groups.append((group_segs, group_ids))

        # 生成合并后的曲线
        result = []
        for gi, (segs, ids) in enumerate(merged_groups):
            if not segs:
                continue
            closed = False
            if len(segs) > 1:
                start_pt = self._first_pt(segs)
                end_pt = self._last_pt(segs)
                if np.linalg.norm(start_pt - end_pt) <= 0.05:
                    closed = True
            result.append({
                "id": f"G{gi:03d}",
                "boundary_ids": ids,
                "segments": segs,
                "closed": closed,
                "type": "merged_bezier",
                "segment_count": len(segs),
            })

        return result

    def _g1_ok(self, t1, t2):
        return self._tangent_angle(t1, t2) <= self.g1_angle_deg

    @staticmethod
    def _first_pt(segments):
        return np.array(segments[0]["p0"])

    @staticmethod
    def _last_pt(segments):
        return np.array(segments[-1]["p3"])

    def _group_segments(self, group):
        segments = []
        for c in group:
            segments.extend(c["segments"])
        return segments
