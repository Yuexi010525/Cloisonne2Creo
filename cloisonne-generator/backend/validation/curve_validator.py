"""
CurveValidator - 曲线工程验证模块
规格书第26-30章 + V2.1 (ChatGPT审查意见):
- 最小线间距检查: 改为 Curve-Curve 真几何距离 (Shapely distance)
- 最小曲率半径检查
- 自交检查: 改为 LineString.is_simple 真几何检测
- 线条拓扑检查（Boundary Graph）
V2.1: 不再用"采样点距离"冒充"曲线距离"，避免假阳性/假阴性
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

        # 1. 最小曲率半径检查（保留采样法，曲率有数学定义）
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

        # 2. V2.1: 用Shapely构建每条曲线的LineString做真几何检测
        from shapely.geometry import LineString
        line_map = {}
        for c in curves:
            pts = []
            for si, seg in enumerate(c["segments"]):
                for i in range(20):  # 高密度采样构建折线
                    t = i / 20
                    pts.append((float(self._bezier_point(seg, t)[0]),
                                float(self._bezier_point(seg, t)[1])))
            # 去重连续重复点
            dedup = []
            for p in pts:
                if not dedup or (abs(dedup[-1][0]-p[0]) > 1e-9 or
                                 abs(dedup[-1][1]-p[1]) > 1e-9):
                    dedup.append(p)
            if len(dedup) >= 2:
                try:
                    line_map[c["id"]] = LineString(dedup)
                except Exception:
                    pass

        # 3. V2.1: 自交检查（真几何：LineString.is_simple）
        # 闭合环(is_simple=True)正常；蝴蝶结/自交叉(is_simple=False)报错
        for c in curves:
            line = line_map.get(c["id"])
            if line is None or line.is_simple:
                continue
            result["intersection_count"] += 1
            if len(result["intersections"]) < 20:
                # 找自交点：曲线与自身的intersection中非端点部分
                try:
                    self_inter = line.intersection(line)
                    pt = self._first_self_intersection_point(line, self_inter)
                except Exception:
                    pt = [round(float(line.coords[0][0]), 3),
                          round(float(line.coords[0][1]), 3)]
                result["intersections"].append({
                    "curve_id": c["id"],
                    "point": pt,
                })

        # 4. V2.1: 线距检查（Curve-Curve minimum distance，Shapely）
        ids = list(line_map.keys())
        for i in range(len(ids)):
            la = line_map[ids[i]]
            for j in range(i + 1, len(ids)):
                lb = line_map[ids[j]]
                try:
                    if la.intersects(lb):
                        continue  # 相交（T型连接点）不算线距冲突
                    d = la.distance(lb)
                except Exception:
                    continue
                if d < self.min_spacing_mm:
                    result["spacing_violation_count"] += 1
                    if len(result["spacing_violations"]) < 20:
                        result["spacing_violations"].append({
                            "curve_a": ids[i],
                            "curve_b": ids[j],
                            "distance_mm": round(float(d), 4),
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

    def _first_self_intersection_point(self, line, self_inter):
        """找出自交点的近似坐标（曲线自身上非首尾的交点）"""
        try:
            from shapely.geometry import Point
            # 自交点 = 与自身重叠/交叉的点；取非端点处的交点
            for geom in getattr(self_inter, "geoms", [self_inter]):
                if geom.geom_type in ("Point",):
                    return [round(float(geom.x), 3), round(float(geom.y), 3)]
                if geom.geom_type == "MultiPoint":
                    for g in geom.geoms:
                        return [round(float(g.x), 3), round(float(g.y), 3)]
            # 兜底：返回曲线的中间点
            mid = line.interpolate(line.length / 2)
            return [round(float(mid.x), 3), round(float(mid.y), 3)]
        except Exception:
            return [0.0, 0.0]

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
