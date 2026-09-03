# -*- coding: utf-8 -*-
"""
LineArtPipeline - 黑白线稿专用管线 (V2.1 线稿模式)
规格书(V2.1线稿模式):
  彩色图 = Region → SharedBoundary
  黑白线稿 = Stroke → Skeleton(中心线)
  Line Art 模式禁止使用 SharedBoundaryExtractor, 直接 Black Mask → Skeleton。
流程: 原图 → BW二值化 → Skeletonize → Skeleton Graph → Spur Pruning
      → 简化+Bezier拟合 → 曲线连续性合并 → 工程验证 → SVG/DXF/IBL/JSON
复用: CurveSimplifier, BezierFitter, CurveMerger, CurveValidator, 全部 Exporters
不自研: 骨架化(skimage), 二值化(OpenCV Otsu)
"""
import sys
import os
import numpy as np
import cv2
import base64
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.lineart.detector import LineArtDetector
from backend.lineart.preprocess import LineArtPreprocess
from backend.lineart.skeleton import LineArtSkeleton
from backend.lineart.graph import SkeletonGraph
from backend.lineart.pruning import SpurPruner
from backend.curve.simplifier import CurveSimplifier
from backend.curve.bezier_fitter import BezierFitter
from backend.curve.curve_merger import CurveMerger
from backend.validation.curve_validator import CurveValidator
from exporters.svg_exporter import SVGExporter
from exporters.dxf_exporter import DXFExporter
from exporters.ibl_exporter import IBLExporter


class LineArtPipeline:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_width_mm = 100.0
        self.output_height_mm = 100.0
        self.merged_curves = None
        self.svg_content = None
        self.debug_dir = self.config.get("debug_dir", None)
        # 调试图计数
        self._debug_counter = 0

    def _save_debug(self, name, data, is_svg=False):
        """保存调试图/文件到 debug_dir"""
        if not self.debug_dir:
            return
        os.makedirs(self.debug_dir, exist_ok=True)
        self._debug_counter += 1
        fname = f"{self._debug_counter:02d}_{name}"
        fpath = os.path.join(self.debug_dir, fname)
        try:
            if is_svg:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(data)
            elif isinstance(data, np.ndarray):
                # OpenCV imwrite 不支持中文路径, 用 imencode + tofile
                ext = os.path.splitext(fname)[1] or ".png"
                ok, buf = cv2.imencode(ext, data)
                if ok:
                    buf.tofile(fpath)
                else:
                    print(f"[warn] debug imencode failed {fname}")
        except Exception as e:
            print(f"[warn] debug save failed {fname}: {e}")

    def run(self, image_bytes, output_width_mm=100, img_format="png"):
        """
        执行线稿管线, 返回与 CloisonnePipeline 兼容的 result dict。
        """
        self.output_width_mm = float(output_width_mm)
        wire_diameter_mm = self.config.get("wire_diameter_mm", 0.6)
        min_spacing_mm = self.config.get("min_wire_spacing_mm", 0.8)
        min_radius_mm = self.config.get("min_radius_mm", 1.0)
        simplify_tolerance_mm = self.config.get("simplify_tolerance_mm", 0.15)
        smoothness = self.config.get("smoothness", 0.7)
        min_spur_length_mm = self.config.get("min_spur_length_mm", 0.8)
        keep_fine_segments = self.config.get("keep_fine_segments", False)
        effective_tolerance = 0.05 + (simplify_tolerance_mm - 0.05) * (0.3 + 0.7 * smoothness)

        # ========== Phase 0: 解码图片 ==========
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("无法解码图片")
        img_h, img_w = img_bgr.shape[:2]
        scale = self.output_width_mm / img_w if img_w > 0 else 1.0
        self.output_height_mm = img_h * scale

        self._save_debug("original.png", img_bgr)

        # ========== Phase 1: BW 二值化 ==========
        preprocessor = LineArtPreprocess(self.config)
        mask, gray = preprocessor.binarize(img_bgr)
        self._save_debug("binary.png", preprocessor.mask_to_uint8(mask))

        # ========== Phase 2: Skeletonize ==========
        skeletor = LineArtSkeleton(self.config)
        skeleton = skeletor.skeletonize(mask)
        self._save_debug("skeleton.png", skeleton)

        # ========== Phase 3: Skeleton Graph ==========
        graph = SkeletonGraph()
        graph.extract(skeleton)

        # ========== Phase 4: Spur Pruning ==========
        pruner = SpurPruner(
            min_spur_length_mm=min_spur_length_mm,
            scale_mm_per_px=scale,
            keep_fine_segments=keep_fine_segments,
        )
        pruner.prune(graph)
        # 修剪后骨架可视化
        pruned_skel = np.zeros_like(skeleton, dtype=bool)
        for edge in graph.edges:
            for (y, x) in edge["points"]:
                if 0 <= y < img_h and 0 <= x < img_w:
                    pruned_skel[y, x] = True
        self._save_debug("pruned_skeleton.png", pruned_skel)

        # ========== Phase 5: 坐标转换 + 简化 + Bezier 拟合 ==========
        simplifier = CurveSimplifier(tolerance_mm=effective_tolerance)
        bezier_fitter = BezierFitter(max_error_mm=effective_tolerance)

        curve_list = []
        simplified_boundaries = []
        for edge in graph.edges:
            # (y,x) → (x_mm, y_mm), y 翻转
            pts_mm = []
            for (y, x) in edge["points"]:
                xm = float(x) * scale
                ym = float(img_h - y) * scale
                pts_mm.append((xm, ym))
            if len(pts_mm) < 2:
                continue
            simplified = simplifier.simplify(pts_mm)
            if len(simplified) < 2:
                continue
            bezier_segs = bezier_fitter.fit(simplified)
            cid = edge["id"]
            length_mm = edge["length_px"] * scale
            curve_list.append({
                "id": cid,
                "segments": bezier_segs,
                "closed": edge.get("closed", False),
                "boundary_ids": [cid],
                "length_mm": round(length_mm, 3),
                "region_a": -1,
                "region_b": -1,
                "source": "lineart_skeleton",
            })
            simplified_boundaries.append({
                "id": cid,
                "points": simplified,
                "closed": edge.get("closed", False),
                "length_mm": round(length_mm, 3),
                "region_a": -1,
                "region_b": -1,
            })

        # ========== Phase 6: 曲线连续性合并 (G0/G1) ==========
        merger = CurveMerger(g0_tolerance_mm=0.01, g1_angle_deg=3.0)
        self.merged_curves = merger.merge(curve_list)

        # ========== Phase 7: 工程验证 ==========
        validator = CurveValidator(min_spacing_mm=min_spacing_mm, min_radius_mm=min_radius_mm)
        validation = validator.validate(self.merged_curves if self.merged_curves else curve_list)
        validation["wire_diameter_mm"] = wire_diameter_mm
        validation["engine"] = "lineart_skeleton"
        validation["curve_group_count"] = len(self.merged_curves) if self.merged_curves else 0
        validation["broken_curve_count"] = 0
        validation["skeleton_edge_count"] = len(graph.edges)
        validation["skeleton_node_count"] = len(graph.nodes)
        validation["pruned_spur_count"] = len(pruner.removed_edges)

        # ========== Phase 8: 导出 ==========
        # SVG
        svg_exporter = SVGExporter(width_mm=self.output_width_mm, height_mm=self.output_height_mm)
        curves_dict = {c["id"]: c["segments"] for c in curve_list}
        self.svg_content = svg_exporter.export(simplified_boundaries, curves_dict)
        self._save_debug("vector_curve.svg", self.svg_content, is_svg=True)

        # 最终预览 SVG (合并后曲线)
        try:
            final_svg = svg_exporter.export_preview_svg(
                simplified_boundaries,
                {mc["id"]: mc["segments"] for mc in (self.merged_curves or curve_list)},
            )
        except Exception:
            final_svg = self.svg_content
        self._save_debug("final_preview.svg", final_svg, is_svg=True)

        # DXF
        dxf_b64 = None
        try:
            dxf_exporter = DXFExporter()
            tmp_dxf = os.path.join(tempfile.gettempdir(), "cloisonne_lineart.dxf")
            dxf_exporter.export(self.merged_curves if self.merged_curves else curve_list, tmp_dxf)
            with open(tmp_dxf, "rb") as f:
                dxf_b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            print(f"[warn] DXF导出失败: {e}")

        # IBL
        ibl_text = None
        try:
            ibl_exporter = IBLExporter()
            ibl_text = ibl_exporter.get_raw_text(self.merged_curves if self.merged_curves else curve_list)
        except Exception as e:
            print(f"[warn] IBL导出失败: {e}")

        # 预览图 (base64)
        preview_images = self._generate_previews(img_bgr, mask, skeleton, pruned_skel, curve_list)

        merged_curves_data = []
        for mc in (self.merged_curves if self.merged_curves else []):
            merged_curves_data.append({
                "id": mc["id"],
                "boundary_ids": mc.get("boundary_ids", []),
                "closed": mc.get("closed", False),
                "segment_count": mc.get("segment_count", len(mc["segments"])),
                "length_mm": round(sum(self._seg_len(s) for s in mc["segments"]), 3),
            })

        result = {
            "image_info": {
                "width_px": int(img_w),
                "height_px": int(img_h),
                "output_width_mm": round(self.output_width_mm, 2),
                "output_height_mm": round(self.output_height_mm, 2),
                "scale_mm_per_px": round(scale, 6),
            },
            "engine": "lineart_skeleton",
            "mode": "lineart",
            "color_palette": [],
            "regions": [],
            "boundaries": [
                {"id": b["id"], "length_mm": b["length_mm"], "closed": b["closed"],
                 "region_a": -1, "region_b": -1, "point_count": len(b["points"])}
                for b in simplified_boundaries
            ],
            "curves": {
                c["id"]: {"segment_count": len(c["segments"]), "segments": c["segments"]}
                for c in curve_list
            },
            "merged_curves": merged_curves_data,
            "boundary_graph": {"nodes": [], "edges": []},
            "validation": validation,
            "svg": self.svg_content,
            "dxf_base64": dxf_b64,
            "ibl_text": ibl_text,
            "preview_images": preview_images,
            "repair_records": [],
            "config": {
                "smoothness": smoothness,
                "min_spur_length_mm": min_spur_length_mm,
                "keep_fine_segments": keep_fine_segments,
                "skeleton_method": self.config.get("skeleton_method", "skeletonize"),
            },
            "lineart_stats": {
                "skeleton_edges": len(graph.edges),
                "skeleton_nodes": len(graph.nodes),
                "pruned_spurs": len(pruner.removed_edges),
                "curve_count": len(curve_list),
                "merged_curve_count": len(self.merged_curves) if self.merged_curves else 0,
            },
        }
        result = self._to_native(result)
        return result

    def _seg_len(self, seg):
        p0 = np.array(seg["p0"])
        p3 = np.array(seg["p3"])
        return float(np.linalg.norm(p3 - p0))

    @staticmethod
    def _to_native(obj):
        if isinstance(obj, dict):
            return {k: LineArtPipeline._to_native(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [LineArtPipeline._to_native(v) for v in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    def _generate_previews(self, img_bgr, mask, skeleton, pruned_skel, curve_list):
        """生成预览图 base64"""
        previews = {}
        h, w = img_bgr.shape[:2]

        def to_b64(arr):
            _, buf = cv2.imencode(".png", arr)
            return base64.b64encode(buf).decode()

        # 原图
        previews["original"] = to_b64(img_bgr)
        # 二值Mask
        mask_vis = cv2.cvtColor((mask.astype(np.uint8) * 255), cv2.COLOR_GRAY2BGR)
        previews["binary"] = to_b64(mask_vis)
        # 骨架
        skel_vis = cv2.cvtColor((skeleton.astype(np.uint8) * 255), cv2.COLOR_GRAY2BGR)
        previews["skeleton"] = to_b64(skel_vis)
        # 修剪后骨架
        pruned_vis = cv2.cvtColor((pruned_skel.astype(np.uint8) * 255), cv2.COLOR_GRAY2BGR)
        previews["pruned_skeleton"] = to_b64(pruned_vis)

        # 最终曲线叠加图
        overlay = np.full((h, w, 3), 255, dtype=np.uint8)
        scale = self.output_width_mm / w if w > 0 else 1.0
        for c in curve_list:
            for seg in c["segments"]:
                # 采样 Bezier
                pts = []
                for t in np.linspace(0, 1, 20):
                    p0 = np.array(seg["p0"]); p1 = np.array(seg["p1"])
                    p2 = np.array(seg["p2"]); p3 = np.array(seg["p3"])
                    pt = (1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t**2*p2 + t**3*p3
                    pts.append(pt)
                for i in range(len(pts)-1):
                    x1 = int(pts[i][0] / scale)
                    y1 = int(h - pts[i][1] / scale)
                    x2 = int(pts[i+1][0] / scale)
                    y2 = int(h - pts[i+1][1] / scale)
                    cv2.line(overlay, (x1, y1), (x2, y2), (0, 0, 255), 1)
        previews["final_curves"] = to_b64(overlay)
        return previews
