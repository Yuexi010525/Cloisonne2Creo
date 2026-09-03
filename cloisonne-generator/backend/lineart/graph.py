# -*- coding: utf-8 -*-
"""
SkeletonGraph - 骨架图提取
规格书(V2.1线稿模式): 8邻域统计邻接数 (1=endpoint, 2=normal, >=3=junction),
骨架 → Graph(Node/Edge) → ordered points Path。
交叉处保留 Junction Node, 不强行合并。
不自研图算法库, 用 NumPy 邻接扫描即可。
"""
import numpy as np
from collections import deque


# 8 邻域偏移 (dy, dx)
NEIGHBORS8 = [(-1, -1), (-1, 0), (-1, 1),
              (0, -1),           (0, 1),
              (1, -1),  (1, 0),  (1, 1)]


class SkeletonGraph:
    def __init__(self):
        self.nodes = {}       # node_id -> {"y":, "x":, "type": "endpoint"/"junction", "degree":}
        self.edges = []       # list of {"id":, "node_a":, "node_b":, "points": [(y,x),...], "length_px":}
        self._node_counter = 0

    def _new_node(self, y, x, ntype, degree):
        nid = self._node_counter
        self._node_counter += 1
        self.nodes[nid] = {"y": int(y), "x": int(x), "type": ntype, "degree": int(degree)}
        return nid

    def extract(self, skeleton):
        """
        输入: skeleton bool array (H, W), True=骨架像素
        输出: self (nodes + edges, edges.points 是 ordered (y,x) 列表)
        """
        skel = np.asarray(skeleton, dtype=bool)
        H, W = skel.shape

        # 找所有骨架像素
        ys, xs = np.where(skel)
        if len(ys) == 0:
            return self

        # 用 set 加速邻接查询
        pixel_set = set(zip(ys.tolist(), xs.tolist()))

        # 计算每个像素的 8 邻域度数
        degree = {}
        for (y, x) in pixel_set:
            cnt = 0
            for dy, dx in NEIGHBORS8:
                if (y + dy, x + dx) in pixel_set:
                    cnt += 1
            degree[(y, x)] = cnt

        # 分类节点
        endpoints = {p for p, d in degree.items() if d == 1}
        junctions = {p for p, d in degree.items() if d >= 3}
        # normal = degree == 2 (或孤立点 degree==0)

        # 节点映射: pixel -> node_id
        node_map = {}
        for p in endpoints:
            node_map[p] = self._new_node(p[0], p[1], "endpoint", 1)
        for p in junctions:
            node_map[p] = self._new_node(p[0], p[1], "junction", degree[p])

        # 已访问的 normal 像素 (从边遍历中标记)
        visited_normal = set()
        edge_id = 0

        def walk_edge(start_pixel, first_step):
            """从 start_pixel(节点) 出发, 沿 first_step 方向走, 直到遇到下一个节点"""
            points = [start_pixel]
            cur = first_step
            prev = start_pixel
            while True:
                points.append(cur)
                if cur in node_map:
                    # 到达另一个节点
                    return cur, points
                # normal 像素, 找下一个未访问的邻居
                visited_normal.add(cur)
                next_pixels = []
                for dy, dx in NEIGHBORS8:
                    nb = (cur[0] + dy, cur[1] + dx)
                    if nb in pixel_set and nb != prev:
                        next_pixels.append(nb)
                if not next_pixels:
                    # 死胡同(不应发生, 除非孤立)
                    return None, points
                # 选第一个(骨架 normal 度=2, 只有一个前进方向)
                nxt = next_pixels[0]
                prev = cur
                cur = nxt

        # 从每个节点出发, 遍历所有未访问的边
        for nid, node in list(self.nodes.items()):
            start = (node["y"], node["x"])
            for dy, dx in NEIGHBORS8:
                nb = (start[0] + dy, start[1] + dx)
                if nb not in pixel_set:
                    continue
                # 这条边是否已被遍历? 检查 nb 是否是已访问 normal 或已连接节点
                if nb in visited_normal:
                    continue
                if nb in node_map:
                    # 节点-节点直接相邻(极短边)
                    other_nid = node_map[nb]
                    # 避免重复: 只处理 nid < other_nid
                    if nid < other_nid:
                        self.edges.append({
                            "id": f"E{edge_id:04d}",
                            "node_a": nid, "node_b": other_nid,
                            "points": [start, nb],
                            "length_px": float(np.hypot(nb[0]-start[0], nb[1]-start[1])),
                        })
                        edge_id += 1
                    continue
                # 沿 normal 走
                end_node, pts = walk_edge(start, nb)
                if end_node is not None and end_node in node_map:
                    other_nid = node_map[end_node]
                    if nid < other_nid or (nid == other_nid):
                        # 计算长度
                        length = sum(np.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])
                                     for i in range(len(pts)-1))
                        self.edges.append({
                            "id": f"E{edge_id:04d}",
                            "node_a": nid, "node_b": other_nid,
                            "points": pts,
                            "length_px": float(length),
                        })
                        edge_id += 1

        # 处理闭合环(没有 endpoint/junction 的独立环)
        # 找所有未访问的 normal 像素
        ring_starts = [p for p in pixel_set
                        if p not in node_map and p not in visited_normal and degree.get(p, 0) == 2]
        for start in ring_starts:
            if start in visited_normal:
                continue
            # 沿环走一圈
            pts = [start]
            prev = None
            cur = start
            while True:
                visited_normal.add(cur)
                next_pixels = []
                for dy, dx in NEIGHBORS8:
                    nb = (cur[0] + dy, cur[1] + dx)
                    if nb in pixel_set and nb != prev and degree.get(nb, 0) == 2:
                        next_pixels.append(nb)
                if not next_pixels:
                    break
                nxt = next_pixels[0]
                if nxt == start and len(pts) > 2:
                    # 闭合
                    pts.append(start)
                    break
                prev = cur
                cur = nxt
                pts.append(cur)
                if len(pts) > len(pixel_set) + 10:
                    break
            if len(pts) >= 3:
                length = sum(np.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])
                             for i in range(len(pts)-1))
                self.edges.append({
                    "id": f"E{edge_id:04d}",
                    "node_a": -1, "node_b": -1,  # 环无节点
                    "points": pts,
                    "length_px": float(length),
                    "closed": True,
                })
                edge_id += 1

        return self

    def get_edge_points_xy(self, edge):
        """把 (y,x) points 转成 (x,y) 列表"""
        return [(float(p[1]), float(p[0])) for p in edge["points"]]
