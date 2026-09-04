# -*- coding: utf-8 -*-
"""Optimize CurveMerger.merge: endpoint grid index.
Only curves whose endpoints fall in the same/adjacent grid cell (distance
<= g0_tolerance) are considered, so the O(N^2) full scan becomes near-linear.
Merging logic (G0/G1, 4 modes, flip) is unchanged -> identical results.
"""
p = r'F:\000-deepseek\掐丝模型生成器\cloisonne-generator\backend\curve\curve_merger.py'
d = open(p, 'rb').read().decode('utf-8')

start_marker = '    def merge(self, curves):'
end_marker = '    def _g1_ok(self, t1, t2):'
si = d.index(start_marker)
ei = d.index(end_marker)

new_merge = '''    def merge(self, curves):
        """
        合并连续曲线（V2.1: 支持自动翻转方向）
        curves: [{"id", "segments": [...]}, ...]
        返回: [{"id", "boundary_ids", "segments", "closed", "type": "merged"}, ...]
        V2.3.2: 端点网格索引, 只检查端点距离 <= g0_tolerance 的邻域候选,
        把 O(N^2) 全量扫描降为近线性, 修复复杂图合并卡死(结果与全量扫描一致)。
        """
        if not curves:
            return []

        # 预计算每条曲线的 segments/端点/切线(避免内层反复重算)
        items = []
        for c in curves:
            segs = c.get("segments") or []
            if not segs:
                continue
            n_start = np.array(segs[0]["p0"], dtype=np.float64)
            n_end = np.array(segs[-1]["p3"], dtype=np.float64)
            n_start_tan = self._seg_start_tangent(segs[0])
            n_end_tan = self._seg_end_tangent(segs[-1])
            items.append({
                "id": c["id"],
                "normal": segs,
                "flipped": self._reverse_segments(segs),
                "n_start": n_start,
                "n_end": n_end,
                "n_start_tan": n_start_tan,
                "n_end_tan": n_end_tan,
                "used": False,
            })
        if not items:
            return []

        # 端点网格索引: cell = 2*g0_tol, 保证"距离<=g0_tol 的端点对必在同一或相邻 cell"
        cell = max(self.g0_tolerance_mm * 2.0, 1e-6)
        grid = {}
        for i, it in enumerate(items):
            for pt in (it["n_start"], it["n_end"]):
                key = (int(np.floor(pt[0] / cell)), int(np.floor(pt[1] / cell)))
                grid.setdefault(key, set()).add(i)

        def _neighbors(pt):
            kx = int(np.floor(pt[0] / cell))
            ky = int(np.floor(pt[1] / cell))
            cand = set()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cand |= grid.get((kx + dx, ky + dy), set())
            return cand

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

                # 只检查端点落在当前 group 端点邻域的候选
                candidates_set = _neighbors(cur_start) | _neighbors(cur_end)
                for i in candidates_set:
                    other = items[i]
                    if other["used"]:
                        continue
                    n_start = other["n_start"]
                    n_end = other["n_end"]
                    n_start_tan = other["n_start_tan"]
                    n_end_tan = other["n_end_tan"]
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

'''
d = d[:si] + new_merge + d[ei:]
open(p, 'wb').write(d.encode('utf-8'))
print('patched curve_merger (endpoint grid index)')
