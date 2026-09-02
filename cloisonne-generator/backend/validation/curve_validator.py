"""
CurveValidator - 曲线工程验证模块
规格书第26-30章:
- 最小线间距检查
- 最小曲率半径检查
- 自交检查
- 线条拓扑检查（Boundary Graph）
"""
import numpy as np


class CurveValidator:
    def __init__(self, min_spacing_mm=0.8, min_radius_mm=1.0):
        self.min_spacing_mm = min_spacing_mm
        self.min_radius_mm = min_radius_mm

    def _bezier_point(self, seg, t):
        p0 = np.array(seg["p0"])
        p1 = np.array(seg["p1"])
        p2 = np.array(seg["p2"])
        p3 = np.array(seg["p3"])
        mt = 1 - t
        return (mt**3 * p0 + 3*mt**2*t * p1 + 3*mt*t**2 * p2 + t**3 * p3)

    def _bezier_tangent(self, seg, t):
        """贝塞尔曲线切线方向"""
        p0 = np.array(seg["p0"])
        p1 = np.array(seg["p1"])
        p2 = np.array(seg["p2"])
        p3 = np.array(seg["p3"])
        mt = 1 - t
        # B'(t) = 3(1-t)^2(P1-P0) + 6(1-t)t(P2-P1) + 3t^2(P3-P2)
        return (3*mt**2 * (p1 - p0) +
                6*mt*t * (p2 - p1) +
                3*t**2 * (p3 - p2))

    def _bezier_curvature(self, seg, t):
        """贝塞尔曲线在t处的曲率"""
        p0 = np.array(seg["p0"])
        p1 = np.array(seg["p1"])
        p2 = np.array(seg["p2"])
        p3 = np.array(seg["p3"])
        mt = 1 - t

        # B'(t)
        d1 = (3*mt**2 * (p1 - p0) + 6*mt*t * (p2 - p1) + 3*t**2 * (p3 - p2))
        # B''(t)
        d2 = (6*mt * (p2 - 2*p1 + p0) + 6*t * (p3 - 2*p2 + p1))

        n1 = np.linalg.norm(d1)
        if n1 < 1e-10:
            return 0.0
        # 曲率 k = |B' × B''| / |B'|^3  (2D叉积标量)
        cross = d1[0] * d2[1] - d1[1] * d2[0]
        curvature = abs(cross) / (n1 ** 3)
        return curvature

    def validate(self, curves, samples_per_seg=10):
        """
        验证所有曲线
        curves: [{"id", "segments", ...}]
        返回: {"curve_count", "intersection_count", "spacing_violation_count",
               "small_radius_count", "broken_curve_count", "invalid_curve_count",
               "spacing_violations": [...], "small_radius": [...], "intersections": [...]}
        """
        result = {
            "curve_count": sum(c.get("segment_count", len(c["segments"])) for c in curves),
            "boundary_count": len(curves),
            "intersection_count": 0,
            "spacing_violation_count": 0,
            "small_radius_count": 0,
            "broken_curve_count": 0,
            "invalid_curve_count": 0,
            "spacing_violations": [],
            "small_radius": [],
            "intersections": [],
        }

        # 1. 最小曲率半径检查
        for c in curves:
            for si, seg in enumerate(c["segments"]):
                for i in range(samples_per_seg + 1):
                    t = i / samples_per_seg
                    curvature = self._bezier_curvature(seg, t)
                    if curvature > 1e-6:
                        radius = 1.0 / curvature
                        if radius < self.min_radius_mm:
                            result["small_radius_count"] += 1
                            if len(result["small_radius"]) < 20:
                                result["small_radius"].append({
                                    "curve_id": c["id"],
                                    "segment": si,
                                    "t": round(t, 3),
                                    "radius_mm": round(radius, 4),
                                })

        # 2. 曲线间最小间距检查（空间哈希网格，避免O(n²)）
        # 只检查不同曲线之间的邻近点对
        cell_size = max(self.min_spacing_mm, 0.5)  # 网格单元大小
        grid = {}  # (gx, gy) -> [(curve_id, point)]
        spacing_violated_pairs = set()  # 记录 (curve_a, curve_b) 已报冲突

        for c in curves:
            for si, seg in enumerate(c["segments"]):
                for i in range(samples_per_seg + 1):
                    t = i / samples_per_seg
                    pt = self._bezier_point(seg, t)
                    gx = int(pt[0] // cell_size)
                    gy = int(pt[1] // cell_size)
                    grid.setdefault((gx, gy), []).append((c["id"], pt))

        # 检查相邻9个网格中的点对
        checked = set()
        for (gx, gy), points in grid.items():
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    ng = grid.get((gx + dx, gy + dy), [])
                    for a_idx in range(len(points)):
                        ca, pa = points[a_idx]
                        for cb, pb in ng:
                            if ca == cb:
                                continue
                            key = (ca, cb) if ca < cb else (cb, ca)
                            if key in checked:
                                continue
                            d = np.linalg.norm(pa - pb)
                            if d < self.min_spacing_mm:
                                checked.add(key)
                                result["spacing_violation_count"] += 1
                                if len(result["spacing_violations"]) < 20:
                                    result["spacing_violations"].append({
                                        "curve_a": ca,
                                        "curve_b": cb,
                                        "distance_mm": round(float(d), 4),
                                    })

        # 3. 自交检查（曲线内部是否相交）
        # 简化检查：同一条曲线内采样点是否出现重复/极近位置
        for c in curves:
            pts = [self._bezier_point(seg, t) for seg in c["segments"]
                   for t in np.linspace(0, 1, 5)]
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    if j - i < 2:  # 跳过相邻点
                        continue
                    d = np.linalg.norm(pts[i] - pts[j])
                    if d < 0.05:  # 0.05mm内视为自交
                        result["intersection_count"] += 1
                        if len(result["intersections"]) < 20:
                            result["intersections"].append({
                                "curve_id": c["id"],
                                "point": [round(float(pts[i][0]), 3), round(float(pts[i][1]), 3)],
                            })

        # 状态判定
        result["status"] = "ok"
        if (result["intersection_count"] > 0 or
            result["broken_curve_count"] > 0 or
            result["invalid_curve_count"] > 0):
            result["status"] = "error"
        elif (result["spacing_violation_count"] > 0 or
              result["small_radius_count"] > 0):
            result["status"] = "warning"

        return result

    def build_boundary_graph(self, curves):
        """
        构建边界拓扑图（规格书第30章）
        每个交叉点定义为Node，每条连续曲线定义为Edge
        """
        nodes = []  # [{"id", "point", "edges": [...]}]
        edges = []  # [{"id", "curve_id", "start_node", "end_node", "closed"}]

        node_map = {}  # (round(x,2), round(y,2)) -> node_id

        def get_node(point):
            key = (round(point[0], 2), round(point[1], 2))
            if key not in node_map:
                node_map[key] = len(nodes)
                nodes.append({"id": f"N{len(nodes):03d}", "point": [key[0], key[1]], "edges": []})
            return node_map[key]

        for ci, c in enumerate(curves):
            start_pt = c["segments"][0]["p0"]
            end_pt = c["segments"][-1]["p3"]
            if c.get("closed", False):
                n = get_node(start_pt)
                edges.append({"id": f"E{ci:03d}", "curve_id": c["id"],
                              "start_node": n, "end_node": n, "closed": True})
                nodes[n]["edges"].append(ci)
            else:
                ns = get_node(start_pt)
                ne = get_node(end_pt)
                edges.append({"id": f"E{ci:03d}", "curve_id": c["id"],
                              "start_node": ns, "end_node": ne, "closed": False})
                nodes[ns]["edges"].append(ci)
                nodes[ne]["edges"].append(ci)

        return {"nodes": nodes, "edges": edges}
