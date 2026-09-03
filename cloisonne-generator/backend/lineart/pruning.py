# -*- coding: utf-8 -*-
"""
SpurPruner - 骨架毛刺修剪
规格书(V2.1线稿模式): 短于 0.8mm 的末端分支默认删除(Spur Pruning)。
不能简单删除所有短线(眼睫毛/鸟嘴/花蕊可能本来就是短线), 提供"保留细小线段"开关。
迭代修剪(剪完一次可能产生新的 endpoint)。
"""
import numpy as np


class SpurPruner:
    def __init__(self, min_spur_length_mm=0.8, scale_mm_per_px=0.1,
                 keep_fine_segments=False):
        self.min_spur_length_mm = min_spur_length_mm
        self.scale = scale_mm_per_px
        self.keep_fine_segments = keep_fine_segments
        self.removed_edges = []

    def prune(self, graph):
        """
        输入: SkeletonGraph (nodes + edges)
        输出: 修剪后的 graph (原地修改)
        """
        if self.keep_fine_segments:
            return graph

        min_spur_px = self.min_spur_length_mm / max(self.scale, 1e-9)

        for iteration in range(20):  # 最多迭代20轮
            removed_any = False
            # 找所有 endpoint 节点
            endpoint_ids = {nid for nid, n in graph.nodes.items() if n["type"] == "endpoint"}
            if not endpoint_ids:
                break

            # 找连接 endpoint 的短边
            edges_to_remove = set()
            for i, edge in enumerate(graph.edges):
                if edge.get("closed"):
                    continue
                na, nb = edge["node_a"], edge["node_b"]
                # 一端是 endpoint, 另一端是 junction 或 endpoint
                if na in endpoint_ids or nb in endpoint_ids:
                    if edge["length_px"] < min_spur_px:
                        edges_to_remove.add(i)

            if not edges_to_remove:
                break

            # 删除边
            new_edges = []
            for i, edge in enumerate(graph.edges):
                if i in edges_to_remove:
                    self.removed_edges.append(edge)
                    removed_any = True
                else:
                    new_edges.append(edge)
            graph.edges = new_edges

            # 重新计算节点度数, 更新 endpoint/junction 分类
            # 先清空孤立节点
            degree_count = {}
            for edge in graph.edges:
                if edge.get("closed"):
                    continue
                na, nb = edge["node_a"], edge["node_b"]
                if na >= 0:
                    degree_count[na] = degree_count.get(na, 0) + 1
                if nb >= 0:
                    degree_count[nb] = degree_count.get(nb, 0) + 1

            # 更新节点类型, 删除孤立节点
            nodes_to_keep = {}
            for nid, node in graph.nodes.items():
                deg = degree_count.get(nid, 0)
                if deg == 0:
                    continue  # 孤立节点删除
                if deg == 1:
                    node["type"] = "endpoint"
                elif deg >= 3:
                    node["type"] = "junction"
                else:
                    node["type"] = "normal"
                node["degree"] = deg
                nodes_to_keep[nid] = node
            graph.nodes = nodes_to_keep

            if not removed_any:
                break

        return graph
