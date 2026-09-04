# -*- coding: utf-8 -*-
"""Fix _prune_overlap: O(N^2) -> O(N log N) using shapely STRtree spatial index.
The naive version did unary_union(all-other-bounds) + buffer for EVERY closed
boundary, which explodes on complex images (hangs + 770MB memory)."""
import re

p = r'F:\000-deepseek\掐丝模型生成器\cloisonne-generator\backend\boundary\shared_boundary.py'
d = open(p, 'rb').read().decode('utf-8')

start_marker = '    def _prune_overlap(self, overlap_tol_mm=0.12):'
end_marker = '    def _snap_endpoints(self, tol_mm=0.3):'
si = d.index(start_marker)
ei = d.index(end_marker)

new_method = '''    def _prune_overlap(self, overlap_tol_mm=0.12):
        """
        重叠裁剪：对闭合边界, 从其中减去"被其他边界覆盖"的子段。
        背景-花瓣共享边界被buffer过度提取成"闭合轮廓"(含花瓣间共享段),
        与真正的花瓣间边界重叠 → 假线距冲突。
        只裁剪闭合边界, 避免误伤正常开放边界(Test04因过度裁剪冲突3→12)。
        V2.3.2: 用 STRtree 空间索引把 O(N^2) 改为 O(N log N),
        避免复杂彩色图(闭合边界多)时 unary_union+buffer 全量组合导致卡死/内存爆炸。
        """
        try:
            from shapely.geometry import LineString
            from shapely.ops import unary_union
            from shapely.strtree import STRtree
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
        geoms = [lj for _, lj, _, _, _ in line_objs]
        # 空间索引: 只处理与当前边界真正相交/邻近的少数候选
        tree = STRtree(geoms)
        closed_count = sum(1 for _, _, is_c, _, _ in line_objs if is_c)
        # 保护上限: 闭合边界过多时(极端复杂图)跳过裁剪, 优先保证不卡死
        if closed_count > 400:
            if os.environ.get("PRUNE_DEBUG"):
                print(f"[prune] skip: closed_count={closed_count} too large")
            return
        for i in range(len(line_objs)):
            bi, ln, is_closed, ra, rb = line_objs[i]
            # 只裁剪"含被子段覆盖"的闭合边界: 只有闭合边界与其他边界有
            # 显著重叠(>2mm)时才需要裁剪(buffer过度提取特征);
            # 普通闭合轮廓(Test04猫体)与其他边界仅节点相接, 不裁剪。
            if not is_closed or (ra != 0 and rb != 0):
                continue
            try:
                # bbox 级候选(空间索引), 再精确过滤距离
                cand = tree.query(ln)
                others = []
                for c in cand:
                    j = int(c)
                    if j == i:
                        continue
                    lj = geoms[j]
                    if ln.distance(lj) < (overlap_tol_mm * 2.0 + 1e-6):
                        others.append(lj)
                if not others:
                    continue
                o_union = unary_union(others)
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

'''
d = d[:si] + new_method + d[ei:]
open(p, 'wb').write(d.encode('utf-8'))
print('patched _prune_overlap with STRtree index')
