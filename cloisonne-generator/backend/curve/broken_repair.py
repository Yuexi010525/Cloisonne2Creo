"""
BrokenCurveRepair - 断线修复模块
规格书V2.0第25章:
- Gap < 0.2mm 自动连接
- 0.2 ~ 1mm 尝试Bezier修复
- > 1mm 默认不修，显示"⚠ 未修复断线"
"""
import numpy as np


class BrokenCurveRepair:
    def __init__(self, gap_auto=0.2, gap_medium=1.0):
        self.gap_auto = gap_auto       # 情况A阈值 <0.2mm
        self.gap_medium = gap_medium   # 情况B阈值 0.2~1mm

    def detect_broken_points(self, points):
        """
        检测折线中的异常断点（规格书第24章）
        如果相邻点距离突然远大于局部点距，认为存在断点
        返回: [{"index", "gap_mm"}, ...]
        """
        if len(points) < 3:
            return []

        # 计算所有相邻点距离
        distances = []
        for i in range(len(points) - 1):
            d = np.sqrt((points[i+1][0]-points[i][0])**2 +
                        (points[i+1][1]-points[i][1])**2)
            distances.append(d)

        if not distances:
            return []

        # 计算正常局部点距（中位数）
        normal_dist = np.median(distances)
        if normal_dist <= 0:
            return []

        broken_points = []
        for i, d in enumerate(distances):
            # 如果距离远大于正常值（比如>5倍）
            if d > normal_dist * 5 and d > self.gap_auto:
                broken_points.append({
                    "index": i,  # 断点位于 points[i] 和 points[i+1] 之间
                    "gap_mm": round(float(d), 3),
                })
        return broken_points

    def repair(self, points):
        """
        修复折线中的断线
        返回: {"points": 修复后的点, "repairs": [修复记录], "failed": [失败记录]}
        """
        broken = self.detect_broken_points(points)
        if not broken:
            return {"points": points, "repairs": [], "failed": []}

        repairs = []
        failed = []

        # 从后往前处理，避免索引失效
        for bp in reversed(broken):
            idx = bp["index"]
            gap = bp["gap_mm"]
            p_prev = points[idx]
            p_next = points[idx + 1]

            if gap < self.gap_auto:
                # 情况A: 微小间隙，直接闭合（用中点）
                mid = [(p_prev[0] + p_next[0]) / 2, (p_prev[1] + p_next[1]) / 2]
                points[idx] = mid
                repairs.append({"index": idx, "type": "auto_close", "gap_mm": gap})

            elif gap <= self.gap_medium:
                # 情况B: 中等间隙，用Bezier平滑连接
                # 在两个端点之间插入中间控制点（沿切线方向延伸）
                p_prev2 = points[idx - 1] if idx >= 1 else p_prev
                p_next2 = points[idx + 2] if idx + 2 < len(points) else p_next

                # 计算两端切线方向
                t1 = np.array(p_prev) - np.array(p_prev2)
                t2 = np.array(p_next2) - np.array(p_next)
                n1 = np.linalg.norm(t1)
                n2 = np.linalg.norm(t2)
                if n1 > 0: t1 = t1 / n1
                if n2 > 0: t2 = t2 / n2

                # 插入两个中间点形成平滑曲线
                d = np.linalg.norm(np.array(p_next) - np.array(p_prev))
                mid1 = np.array(p_prev) + t1 * d * 0.4
                mid2 = np.array(p_next) + t2 * d * 0.4
                mid = [(mid1[0] + mid2[0]) / 2, (mid1[1] + mid2[1]) / 2]

                # 插入点
                points = points[:idx+1] + [mid, p_next] + points[idx+2:]
                repairs.append({"index": idx, "type": "bezier_bridge", "gap_mm": gap})

            else:
                # 情况C: 间隙太大，不自动连接
                failed.append({"index": idx, "gap_mm": gap, "repair_status": "failed"})

        return {"points": points, "repairs": repairs, "failed": failed}
