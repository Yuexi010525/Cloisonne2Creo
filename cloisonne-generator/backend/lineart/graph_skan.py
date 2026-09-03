# -*- coding: utf-8 -*-
"""
SkanSkeletonGraph - Skan 骨架图引擎 (V2.2 默认)
规格书(V2.2 Line Art Engineering):
  - Skan 负责 Skeleton Image → Skeleton Graph → Branch/Path extraction
  - 不再扩展自研 Graph 算法
  - Skan 默认作为 V2.2 LineArt Graph Engine
  - 保留 LegacySkeletonGraph (graph.py) 作为 fallback
  - 统一接口: class SkeletonGraphEngine: def extract(self, skeleton, spacing_mm_per_px)
  - Skan 物理尺度: spacing=[scale_mm_per_px, scale_mm_per_px]
"""
import numpy as np


class SkanSkeletonGraph:
    """Skan 骨架图引擎, 接口与 LegacySkeletonGraph 兼容"""

    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.stats = {
            "skeleton_pixel_count": 0,
            "junction_count": 0,
            "endpoint_count": 0,
            "branch_count": 0,
            "cycle_count": 0,
        }
        self._node_counter = 0

    def extract(self, skeleton, spacing_mm_per_px=0.1):
        """
        输入: skeleton bool array (H, W), spacing_mm_per_px 物理尺度
        输出: self (nodes + edges, 与 LegacySkeletonGraph 兼容格式)
        """
        from skan import Skeleton, summarize

        skel = np.asarray(skeleton, dtype=bool)
        self.stats["skeleton_pixel_count"] = int(skel.sum())

        if not skel.any():
            return self

        # Skan 物理尺度 spacing=[dy, dx]
        spacing = [float(spacing_mm_per_px), float(spacing_mm_per_px)]
        skan_skel = Skeleton(skel, spacing=spacing)

        # summarize 获取 branch 信息
        try:
            summary = summarize(skan_skel, separator='_')
        except TypeError:
            summary = summarize(skan_skel)

        # 收集所有节点 (junction + endpoint)
        # node-id-src / node-id-dst 是 Skan 内部节点 ID
        # 我们需要建立 skan_node_id -> local_node_id 映射
        node_map = {}  # skan_node_id -> local_node_id
        node_info = {}  # skan_node_id -> {"y":, "x":, "type":, "degree":}

        # branch-type: 0=endpoint-endpoint, 1=endpoint-junction, 2=junction-junction, 3=cycle
        endpoint_nodes = set()
        junction_nodes = set()
        cycle_count = 0

        for _, row in summary.iterrows():
            btype = int(row.get("branch_type", -1))
            src_id = int(row["node_id_src"])
            dst_id = int(row["node_id_dst"])

            if btype == 3:
                cycle_count += 1
                # 环没有 endpoint, 两个端点都是 junction 或同一个
                junction_nodes.add(src_id)
                junction_nodes.add(dst_id)
            elif btype == 0:
                # endpoint-endpoint
                endpoint_nodes.add(src_id)
                endpoint_nodes.add(dst_id)
            elif btype == 1:
                # endpoint-junction: 需要判断哪个是 endpoint
                # 通常 src 或 dst 中度数为 1 的是 endpoint
                endpoint_nodes.add(src_id)
                junction_nodes.add(dst_id)
            elif btype == 2:
                # junction-junction
                junction_nodes.add(src_id)
                junction_nodes.add(dst_id)

        # 从坐标列获取节点坐标
        # image_coord_src_0/1 = (y, x) 图像坐标
        for _, row in summary.iterrows():
            src_id = int(row["node_id_src"])
            dst_id = int(row["node_id_dst"])
            src_y = float(row.get("image_coord_src_0", 0))
            src_x = float(row.get("image_coord_src_1", 0))
            dst_y = float(row.get("image_coord_dst_0", 0))
            dst_x = float(row.get("image_coord_dst_1", 0))

            if src_id not in node_info:
                ntype = "junction" if src_id in junction_nodes else "endpoint"
                node_info[src_id] = {"y": src_y, "x": src_x, "type": ntype, "degree": 0}
            if dst_id not in node_info:
                ntype = "junction" if dst_id in junction_nodes else "endpoint"
                node_info[dst_id] = {"y": dst_y, "x": dst_x, "type": ntype, "degree": 0}

        # 计算度数
        for _, row in summary.iterrows():
            src_id = int(row["node_id_src"])
            dst_id = int(row["node_id_dst"])
            if src_id in node_info:
                node_info[src_id]["degree"] += 1
            if dst_id in node_info and dst_id != src_id:
                node_info[dst_id]["degree"] += 1

        # 分配 local node ID
        for skan_id, info in node_info.items():
            local_id = self._node_counter
            self._node_counter += 1
            node_map[skan_id] = local_id
            self.nodes[local_id] = info

        self.stats["junction_count"] = len(junction_nodes)
        self.stats["endpoint_count"] = len(endpoint_nodes)
        self.stats["cycle_count"] = cycle_count
        self.stats["branch_count"] = len(summary)

        # 构建 edges: 用 path_coordinates 获取完整点串
        # Skan 的 path index 与 summary 的行对应
        self.edges = []
        for idx, row in summary.iterrows():
            btype = int(row.get("branch_type", -1))
            src_id = int(row["node_id_src"])
            dst_id = int(row["node_id_dst"])
            local_src = node_map.get(src_id, -1)
            local_dst = node_map.get(dst_id, -1)

            # 获取路径点串
            try:
                coords = skan_skel.path_coordinates(int(idx))
                # coords shape: (N, 2) = [[y, x], ...]
                points = [(float(c[0]), float(c[1])) for c in coords]
            except Exception:
                # fallback: 用端点
                points = [
                    (node_info.get(src_id, {}).get("y", 0), node_info.get(src_id, {}).get("x", 0)),
                    (node_info.get(dst_id, {}).get("y", 0), node_info.get(dst_id, {}).get("x", 0)),
                ]

            if len(points) < 2:
                continue

            # 长度: 用 branch-distance (物理尺度 mm) 转 px, 或直接计算像素距离
            length_mm = float(row.get("branch_distance", 0))
            length_px = length_mm / max(spacing_mm_per_px, 1e-9)

            is_cycle = (btype == 3)
            edge = {
                "id": f"E{idx:04d}",
                "node_a": local_src,
                "node_b": local_dst,
                "points": points,
                "length_px": float(length_px),
                "branch_type": btype,
            }
            if is_cycle:
                edge["closed"] = True
            self.edges.append(edge)

        return self

    def get_edge_points_xy(self, edge):
        """把 (y,x) points 转成 (x,y) 列表"""
        return [(float(p[1]), float(p[0])) for p in edge["points"]]
