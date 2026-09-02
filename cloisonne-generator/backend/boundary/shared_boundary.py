"""
SharedBoundaryExtractor - 公共边界提取模块（项目核心）
规格书第12章: 不能分别提取每个Region外轮廓后叠加
必须寻找 Boundary(A) ∩ Boundary(B)，形成 SharedBoundary(A,B)
每条公共边界只保存一次，A-B和B-A认为是同一条边界。

V2.1 (ChatGPT审查意见): 从"栅格追踪"升级为"矢量几何"
- V2.0: SVG → Raster label_map → pixel tracing（丢点/拓扑错误）
- V2.1: SVG → Vector Region(Shapely Polygon) → boundary(A)∩boundary(B)
        → Shared Vector Boundary（精度高、无栅格误差）
"""
import numpy as np
from collections import defaultdict


class SharedBoundaryExtractor:
    def __init__(self, scale=1.0, min_boundary_length_mm=1.5):
        self.scale = scale
        self.min_boundary_length_mm = min_boundary_length_mm
        self.boundaries = []  # [{id, region_a, region_b, points, length_mm, closed}]
        self.outline_boundaries = []

    # =====================================================================
    # V2.1 矢量几何提取（主路径）
    # =====================================================================
    def extract_vector(self, vtracer_regions, img_height, valid_region_ids=None,
                       region_id_map=None, outline=False, label_map=None):
        """
        用Shapely在矢量几何上求共享边界:
        boundary(A) ∩ boundary(B) = Shared Boundary(A,B)
        vtracer_regions: VTracerAdapter的regions（含Shapely polygon）
        img_height: 原图高度（用于Y轴翻转: SVG y向下 → CAD y向上）
        valid_region_ids: 小区域过滤后仍有效的vtracer region id集合
        region_id_map: {vtracer_id: segmenter_id} 映射（输出的region_a/b用segmenter id）
        outline: 是否同时提取外轮廓（区域与画布边界）
        label_map: VTracer的label_map，用于精确判定region对是否像素级相邻。
                   关键: buffer(包含多边形)会覆盖其内部所有region的边界造成过度提取,
                   必须用label_map相邻关系过滤, 只有真正接触的region对才有共享边界。
        """
        try:
            from shapely.geometry import LineString, MultiLineString, GeometryCollection
            from shapely.ops import linemerge, unary_union
        except ImportError:
            raise RuntimeError("需要安装Shapely: pip install shapely")

        self.boundaries = []
        self.outline_boundaries = []
        boundary_id = 0

        # 用label_map建立精确相邻region对集合（像素级接触）
        adjacent_pairs = set()
        if label_map is not None and label_map.size > 0:
            h_lab, w_lab = label_map.shape
            for yy in range(h_lab):
                row = label_map[yy]
                for xx in range(w_lab - 1):
                    a = int(row[xx]); b = int(row[xx + 1])
                    if a != b and a >= 0 and b >= 0:
                        adjacent_pairs.add((a, b) if a < b else (b, a))
            for yy in range(h_lab - 1):
                row = label_map[yy]; row2 = label_map[yy + 1]
                for xx in range(w_lab):
                    a = int(row[xx]); b = int(row2[xx])
                    if a != b and a >= 0 and b >= 0:
                        adjacent_pairs.add((a, b) if a < b else (b, a))

        polygons = []  # [(vtracer_id, polygon, segmenter_id)]
        for r in vtracer_regions:
            vi = r["id"]
            if valid_region_ids is not None and vi not in valid_region_ids:
                continue
            if r.get("polygon") is None or r["polygon"].is_empty:
                continue
            si = region_id_map.get(vi, vi) if region_id_map else vi
            polygons.append((vi, r["polygon"], si))

        # 区域对：容差方案提取共享边界。
        # VTracer cutout下背景孔洞与前景区域是两条独立生成的Spline(起点/控制点不同)，
        # 数值上不完全重合，严格 boundary∩boundary 只得到碎片。
        # 且方向性不对称：同一边界只能从A或B一侧可靠提取(另一侧gap可能>tol)。
        # 正确做法: 分别取 boundary(A)∩buffer(B) 和 boundary(B)∩buffer(A)，
        # 选长度更长的一条作为共享边界(避免重复线距冲突, 且取到有效侧)
        tol = 0.6  # px 容差（后续还有简化处理）
        for i in range(len(polygons)):
            vi_a, pa, si_a = polygons[i]
            for j in range(i + 1, len(polygons)):
                vi_b, pb, si_b = polygons[j]
                # 同色region(映射到同一segmenter id)之间的边界不是掐丝边界，跳过
                if si_a == si_b:
                    continue
                # label_map相邻验证：只有像素级接触的region对才有共享边界。
                # 过滤"包含关系"造成的过度提取（背景矩形buffer覆盖内部所有region）
                if adjacent_pairs:
                    key = (vi_a, vi_b) if vi_a < vi_b else (vi_b, vi_a)
                    if key not in adjacent_pairs:
                        continue
                try:
                    if not pa.intersects(pb):
                        continue
                    shared_a = pa.boundary.intersection(pb.buffer(tol, quad_segs=2))
                    shared_b = pb.boundary.intersection(pa.buffer(tol, quad_segs=2))
                    la = self._geom_length(shared_a)
                    lb = self._geom_length(shared_b)
                    src = shared_a if la >= lb else shared_b
                except Exception:
                    continue
                # 逐条LineString提取共享边界。
                # 注意: 不能用linemerge硬连接——它会把分离线段用直线跨gap相连,
                # 在边界内部产生跳变(如1.3mm), 触发大量假断线。
                # 分离线段作为独立边界, 由CurveMerger按G0/G1合并成组。
                for geom in self._iter_linestrings(src):
                    coords = list(geom.coords)
                    if len(coords) < 2:
                        continue
                    self._append_boundary(coords, si_a, si_b, False,
                                          img_height, boundary_id)
                    boundary_id += 1

        # 外轮廓（图案整体外边界：所有区域合并后的外环+孔洞环）
        if outline:
            from shapely.ops import unary_union
            overall = unary_union([p for _, p, _ in polygons])
            if overall is not None and not overall.is_empty:
                try:
                    ob = linemerge(overall.boundary)
                    for geom in self._iter_linestrings(ob):
                        coords = list(geom.coords)
                        if len(coords) < 2:
                            continue
                        self._append_boundary(coords, -2, -1, True,
                                              img_height, boundary_id)
                        boundary_id += 1
                except Exception:
                    pass

        # 重叠裁剪：从较长边界中裁掉被其他边界覆盖的子段。
        # buffer过度提取会把"闭合轮廓"算作背景-花瓣共享(含花瓣间共享段),
        # 与真正的花瓣间边界重叠 → 假线距冲突。先裁剪再焊接。
        self._prune_overlap(overlap_tol_mm=0.12)

        # 端点焊接：合并相邻边界在真实交点处因buffer圆角截断产生的微小gap
        # (gap ~0.15mm > CurveMerger G0容差0.01mm, 必须焊接到同一坐标)
        self._snap_endpoints(tol_mm=0.3)

        return self

    def _prune_overlap(self, overlap_tol_mm=0.12):
        """
        重叠裁剪：对闭合边界, 从其中减去"被其他边界覆盖"的子段。
        背景-花瓣共享边界被buffer过度提取成"闭合轮廓"(含花瓣间共享段),
        与真正的花瓣间边界重叠 → 假线距冲突。
        只裁剪闭合边界, 避免误伤正常开放边界(Test04因过度裁剪冲突3→12)。
        """
        try:
            from shapely.geometry import LineString
            from shapely.ops import unary_union
        except ImportError:
            return
        all_bounds = list(self.boundaries) + list(self.outline_boundaries)
        if len(all_bounds) < 2:
            return
        line_objs = []  # [(index_in_all, LineString, is_closed, region_a, region_b)]
        for bi, b in enumerate(all_bounds):
            pts = b["points"]
            if len(pts) < 2:
                continue
            try:
                ln = LineString(pts)
                if ln.length > 0.5:
                    line_objs.append((bi, ln, b.get("closed", False),
                                      b.get("region_a", -1), b.get("region_b", -1)))
            except Exception:
                continue
        if not line_objs:
            return
        import os
        # 预计算所有边界的线并集, 每边界的排除集=并集-自身
        u_all = unary_union([lj for _, lj, _, _, _ in line_objs])
        for i in range(len(line_objs)):
            bi, ln, is_closed, ra, rb = line_objs[i]
            # 只裁剪"含被子段覆盖"的闭合边界: 只有闭合边界与其他边界有
            # 显著重叠(>2mm)时才需要裁剪(buffer过度提取特征);
            # 普通闭合轮廓(Test04猫体)与其他边界仅节点相接, 不裁剪。
            if not is_closed or (ra != 0 and rb != 0):
                continue
            try:
                others_i = [lj for bj, lj, _, _, _ in line_objs if bj != bi]
                o_union = unary_union(others_i)
                if o_union.is_empty:
                    continue
                # 重叠总长度(排除端点相接)
                inter = ln.intersection(o_union)
                overlap_len = 0.0
                if inter.geom_type == "LineString":
                    overlap_len = inter.length
                elif inter.geom_type == "MultiLineString":
                    overlap_len = sum(g.length for g in inter.geoms)
                elif inter.geom_type == "GeometryCollection":
                    overlap_len = sum(g.length for g in inter.geoms
                                      if g.geom_type in ("LineString", "MultiLineString"))
                if overlap_len < 2.0:
                    continue
                exclude_i = o_union.buffer(overlap_tol_mm)
                if exclude_i.is_empty:
                    continue
                cleaned = ln.difference(exclude_i)
            except Exception:
                if os.environ.get("PRUNE_DEBUG"):
                    print(f"[prune] diff异常 bi={bi}")
                continue
            if cleaned is None or cleaned.is_empty:
                continue
            if os.environ.get("PRUNE_DEBUG"):
                print(f"[prune] bi={bi} closed裁剪 {ln.length:.1f}->{cleaned.length:.1f} type={cleaned.geom_type}")
            new_pts = None
            if cleaned.geom_type == "LineString":
                new_pts = [[round(float(x), 4), round(float(y), 4)]
                           for x, y in cleaned.coords]
            elif cleaned.geom_type == "MultiLineString":
                best = max(cleaned.geoms, key=lambda g: g.length)
                new_pts = [[round(float(x), 4), round(float(y), 4)]
                           for x, y in best.coords]
            if not new_pts or len(new_pts) < 2:
                continue
            b = all_bounds[bi]
            b["points"] = new_pts
            b["length_mm"] = round(self._curve_length(new_pts), 3)
            b["point_count"] = len(new_pts)
            closed = False
            if len(new_pts) > 3:
                d = np.sqrt((new_pts[0][0] - new_pts[-1][0])**2 +
                            (new_pts[0][1] - new_pts[-1][1])**2)
                if d < 0.05:
                    closed = True
            b["closed"] = closed

    def _snap_endpoints(self, tol_mm=0.3):
        """
        端点焊接：所有边界端点按距离聚类, gap<tol_mm的合并到聚类质心。
        修复buffer圆角截断(端点短~0.6px)造成的G0不连续, 让CurveMerger能正确合并。
        仅调整端点坐标，不改变边界内部形状。
        """
        all_bounds = list(self.boundaries) + list(self.outline_boundaries)
        if not all_bounds:
            return
        # 收集端点: (boundary, is_start) -> 坐标
        eps = []  # [(bidx_in_all, is_start, coord)]
        for bi, b in enumerate(all_bounds):
            pts = b["points"]
            if len(pts) < 2:
                continue
            eps.append((bi, True, np.array(pts[0])))
            eps.append((bi, False, np.array(pts[-1])))

        # union-find 聚类
        n = len(eps)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # 对每条边界, 若闭合则不参与焊接(避免破坏环)
        closed_flag = [b.get("closed", False) for b in all_bounds]
        for i in range(n):
            for j in range(i + 1, n):
                bi_i, s_i, c_i = eps[i]
                bi_j, s_j, c_j = eps[j]
                # 闭合边界端点不动
                if closed_flag[bi_i] or closed_flag[bi_j]:
                    continue
                # 同一边界的首尾(若接近且非闭合)不焊(应保持开口)
                if bi_i == bi_j:
                    continue
                if np.linalg.norm(c_i - c_j) <= tol_mm:
                    union(i, j)

        # 计算每个聚类的质心
        clusters = {}
        for i in range(n):
            r = find(i)
            clusters.setdefault(r, []).append(i)
        new_coords = {}
        for r, members in clusters.items():
            avg = np.mean([eps[m][2] for m in members], axis=0)
            new_coords[r] = avg

        # 更新端点坐标 + 重算length/closed
        for i in range(n):
            bi, is_start, _ = eps[i]
            r = find(i)
            new_pt = new_coords[r]
            b = all_bounds[bi]
            if len(b["points"]) < 2:
                continue
            if is_start:
                b["points"][0] = [round(float(new_pt[0]), 4), round(float(new_pt[1]), 4)]
            else:
                b["points"][-1] = [round(float(new_pt[0]), 4), round(float(new_pt[1]), 4)]
        for b in all_bounds:
            b["length_mm"] = round(self._curve_length(b["points"]), 3)
            closed = False
            if len(b["points"]) > 3:
                d = np.sqrt((b["points"][0][0] - b["points"][-1][0])**2 +
                            (b["points"][0][1] - b["points"][-1][1])**2)
                if d < 0.05:
                    closed = True
            b["closed"] = closed
            b["point_count"] = len(b["points"])

    def _resample_polyline(self, coords, step_px=1.5):
        """沿折线均匀重采样，保持形状，固定点距"""
        if len(coords) < 2:
            return list(coords)
        pts = [np.array(c, dtype=float) for c in coords]
        result = [list(pts[0])]
        dist_accum = 0.0
        cur = pts[0]
        for i in range(len(pts) - 1):
            nxt = pts[i + 1]
            seg = nxt - cur
            seg_len = float(np.linalg.norm(seg))
            if seg_len <= 0:
                continue
            while dist_accum + seg_len >= step_px:
                t = (step_px - dist_accum) / seg_len
                pt = cur + seg * t
                result.append(list(pt))
                cur = pt
                seg = nxt - cur
                seg_len = float(np.linalg.norm(seg))
                dist_accum = 0.0
                if seg_len <= 1e-9:
                    break
            dist_accum += seg_len
        # 末尾
        if np.linalg.norm(np.array(result[-1]) - pts[-1]) > 1e-9:
            result.append(list(pts[-1]))
        return result

    def _geom_length(self, geom):
        """计算几何的总长度（LineString/MultiLineString/GeometryCollection）"""
        if geom is None or geom.is_empty:
            return 0.0
        if geom.geom_type == "LineString":
            return float(geom.length)
        total = 0.0
        for g in self._iter_linestrings(geom):
            total += g.length
        return float(total)

    def _iter_linestrings(self, geom):
        """迭代几何，产出所有LineString（处理MultiLineString/GeometryCollection）"""
        from shapely.geometry import LineString, MultiLineString, GeometryCollection, Point
        if geom is None or geom.is_empty:
            return
        if geom.geom_type == "LineString":
            yield geom
        elif geom.geom_type == "MultiLineString":
            for g in geom.geoms:
                yield g
        elif geom.geom_type in ("GeometryCollection", "MultiPolygon"):
            for g in getattr(geom, "geoms", []):
                yield from self._iter_linestrings(g)

    def _append_boundary(self, coords, region_a, region_b, is_outline,
                         img_height, boundary_id):
        """把矢量坐标转为mm（Y翻转），追加为一条边界"""
        # 均匀重采样（step=1.5px），消除buffer intersection点距不均，
        # 稳定断线检测与Bezier拟合
        coords = self._resample_polyline(coords, step_px=1.5)
        if len(coords) < 2:
            return
        mm_points = []
        for x, y in coords:
            mm_points.append([
                round(x * self.scale, 4),
                round((img_height - y) * self.scale, 4),
            ])
        length_mm = self._curve_length(mm_points)
        if length_mm < self.min_boundary_length_mm:
            return
        closed = False
        if len(mm_points) > 3:
            d = np.sqrt((mm_points[0][0] - mm_points[-1][0])**2 +
                        (mm_points[0][1] - mm_points[-1][1])**2)
            if d < 0.05:
                closed = True
        entry = {
            "id": f"{'O' if is_outline else 'B'}{boundary_id:03d}",
            "region_a": int(region_a),
            "region_b": int(region_b),
            "points": mm_points,
            "length_mm": round(length_mm, 3),
            "closed": closed,
            "point_count": len(mm_points),
            "is_outline": bool(is_outline),
        }
        if is_outline:
            self.outline_boundaries.append(entry)
        else:
            self.boundaries.append(entry)

    # =====================================================================
    # 旧栅格追踪方法（V2.0保留，兼容旧调用，新管线使用extract_vector）
    # =====================================================================
    def extract(self, regions, label_map):
        """
        提取所有相邻区域对之间的公共边界（V2.0栅格方法，保留兼容）
        regions: RegionSegmenter的regions列表
        label_map: (H, W) 区域标签图
        """
        self.boundaries = []
        self.outline_boundaries = []
        h, w = label_map.shape
        boundary_id = 0

        # 收集每对相邻区域的边界像素
        # 用边像素标记：每个边界像素记录它分隔的两个region
        edge_pixels = defaultdict(list)  # (min_r, max_r) -> [(x,y), ...]
        # 外轮廓像素：区域与背景(-1)的边界
        outline_pixels = defaultdict(list)  # region_id -> [(x,y), ...]

        # 水平边
        for y in range(h):
            for x in range(w - 1):
                a = label_map[y, x]
                b = label_map[y, x + 1]
                if a >= 0 and b >= 0 and a != b:
                    key = (min(a, b), max(a, b))
                    edge_pixels[key].append((x + 0.5, y))  # 边中点
                elif a >= 0 and b < 0:
                    outline_pixels[a].append((x + 0.5, y))
                elif b >= 0 and a < 0:
                    outline_pixels[b].append((x + 0.5, y))

        # 垂直边
        for y in range(h - 1):
            for x in range(w):
                a = label_map[y, x]
                b = label_map[y + 1, x]
                if a >= 0 and b >= 0 and a != b:
                    key = (min(a, b), max(a, b))
                    edge_pixels[key].append((x, y + 0.5))
                elif a >= 0 and b < 0:
                    outline_pixels[a].append((x, y + 0.5))
                elif b >= 0 and a < 0:
                    outline_pixels[b].append((x, y + 0.5))

        # 对每对区域，跟踪连续边界曲线
        for (ra, rb), pixels in edge_pixels.items():
            if len(pixels) < 3:
                continue

            # 转换为像素坐标集合，用于边界跟踪
            pixel_set = set()
            for px, py in pixels:
                pixel_set.add((int(round(px)), int(round(py))))

            # 边界跟踪：提取连续曲线段
            curves = self._trace_boundaries(pixel_set)

            for curve_points in curves:
                if len(curve_points) < 3:
                    continue
                # 转换为mm坐标，Y轴翻转（图片Y向下 -> CAD Y向上）
                mm_points = []
                for px, py in curve_points:
                    mm_points.append([
                        round(px * self.scale, 4),
                        round((h - py) * self.scale, 4),
                    ])

                length_mm = self._curve_length(mm_points)
                if length_mm < self.min_boundary_length_mm:
                    continue

                # 判断是否闭合
                closed = False
                if len(mm_points) > 3:
                    d = np.sqrt((mm_points[0][0] - mm_points[-1][0])**2 +
                                (mm_points[0][1] - mm_points[-1][1])**2)
                    if d < 0.05:  # 0.05mm阈值
                        closed = True

                self.boundaries.append({
                    "id": f"B{boundary_id:03d}",
                    "region_a": int(ra),
                    "region_b": int(rb),
                    "points": mm_points,
                    "length_mm": round(length_mm, 3),
                    "closed": closed,
                    "point_count": len(mm_points),
                    "is_outline": False,
                })
                boundary_id += 1

        return self

    def extract_outline(self, regions, label_map):
        """
        提取外轮廓边界（区域与背景的边界），供"生成外轮廓"选项使用
        规格书四十一章: 是否生成外轮廓
        """
        self.outline_boundaries = []
        h, w = label_map.shape
        outline_id = 0

        # 收集区域与背景的边界像素
        outline_pixels = defaultdict(list)
        for y in range(h):
            for x in range(w - 1):
                a = label_map[y, x]
                b = label_map[y, x + 1]
                if a >= 0 and b < 0:
                    outline_pixels[a].append((x + 0.5, y))
                elif b >= 0 and a < 0:
                    outline_pixels[b].append((x + 0.5, y))
        for y in range(h - 1):
            for x in range(w):
                a = label_map[y, x]
                b = label_map[y + 1, x]
                if a >= 0 and b < 0:
                    outline_pixels[a].append((x, y + 0.5))
                elif b >= 0 and a < 0:
                    outline_pixels[b].append((x, y + 0.5))

        # 对每个区域的外轮廓，跟踪连续曲线
        for region_id, pixels in outline_pixels.items():
            if len(pixels) < 3:
                continue
            pixel_set = set()
            for px, py in pixels:
                pixel_set.add((int(round(px)), int(round(py))))

            curves = self._trace_boundaries(pixel_set)
            for curve_points in curves:
                if len(curve_points) < 3:
                    continue
                mm_points = []
                for px, py in curve_points:
                    mm_points.append([
                        round(px * self.scale, 4),
                        round((h - py) * self.scale, 4),
                    ])
                length_mm = self._curve_length(mm_points)
                if length_mm < self.min_boundary_length_mm:
                    continue
                closed = False
                if len(mm_points) > 3:
                    d = np.sqrt((mm_points[0][0] - mm_points[-1][0])**2 +
                                (mm_points[0][1] - mm_points[-1][1])**2)
                    if d < 0.05:
                        closed = True
                self.outline_boundaries.append({
                    "id": f"O{outline_id:03d}",
                    "region_a": int(region_id),
                    "region_b": -1,  # 背景
                    "points": mm_points,
                    "length_mm": round(length_mm, 3),
                    "closed": closed,
                    "point_count": len(mm_points),
                    "is_outline": True,
                })
                outline_id += 1

        return self.outline_boundaries

    def _trace_boundaries(self, pixel_set):
        """从边界像素集合中跟踪连续曲线（8连通）"""
        remaining = set(pixel_set)
        curves = []

        while remaining:
            # 找一个端点（邻居数<=1），如果没有则从任意点开始（闭合曲线）
            start = None
            for p in remaining:
                neighbors = self._count_neighbors(p, remaining)
                if neighbors <= 1:
                    start = p
                    break
            if start is None:
                start = next(iter(remaining))

            # 从start开始跟踪
            curve = [start]
            remaining.remove(start)
            current = start

            while True:
                # 找下一个未访问的邻居
                next_p = None
                for dx, dy in [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]:
                    np_ = (current[0]+dx, current[1]+dy)
                    if np_ in remaining:
                        next_p = np_
                        break
                if next_p is None:
                    break
                curve.append(next_p)
                remaining.remove(next_p)
                current = next_p

            if len(curve) >= 3:
                curves.append(curve)

        return curves

    def _count_neighbors(self, p, pixel_set):
        count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                if (p[0]+dx, p[1]+dy) in pixel_set:
                    count += 1
        return count

    def _curve_length(self, points):
        length = 0.0
        for i in range(len(points) - 1):
            dx = points[i+1][0] - points[i][0]
            dy = points[i+1][1] - points[i][1]
            length += np.sqrt(dx*dx + dy*dy)
        return length

    def get_boundaries_info(self):
        return [{k: v for k, v in b.items() if k != "points"} for b in self.boundaries]
