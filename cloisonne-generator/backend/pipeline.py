"""
CloisonnePipeline V2.0 - 基于VTracer的掐丝曲线生成管线
规格书V2.0:
- VTracer负责"图片→颜色区域→初始矢量曲线"（不重写）
- 项目特有部分（Shared Boundary + 工程约束 + Creo导出）自己开发
流程: VTracer → Color Regions → Shared Boundary → 工程验证 → SVG/DXF/IBL/JSON
"""
import sys
import os
import numpy as np
import cv2
import base64
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.segmentation.vtracer_adapter import VTracerAdapter
from backend.segmentation.region_segmenter import RegionSegmenter
from backend.boundary.shared_boundary import SharedBoundaryExtractor
from backend.curve.simplifier import CurveSimplifier
from backend.curve.bezier_fitter import BezierFitter
from backend.curve.curve_merger import CurveMerger
from backend.curve.broken_repair import BrokenCurveRepair
from backend.validation.curve_validator import CurveValidator
from exporters.svg_exporter import SVGExporter
from exporters.dxf_exporter import DXFExporter
from exporters.ibl_exporter import IBLExporter
from exporters.json_exporter import JSONExporter


class CloisonnePipeline:
    def __init__(self, config=None):
        self.config = config or {}
        self.vtracer = None
        self.segmenter = None
        self.boundary_extractor = None
        self.simplifier = None
        self.bezier_fitter = None
        self.curve_merger = None
        self.broken_repair = None
        self.validator = None
        self.result = None
        self.svg_content = None
        self.merged_curves = None
        self.output_width_mm = 100.0
        self.output_height_mm = 100.0

    def run(self, image_bytes, output_width_mm=100, img_format="png"):
        """
        执行V2.0完整管线
        返回: {regions, boundaries, curves, merged_curves, validation,
               svg, dxf_b64, ibl_text, preview_images}
        """
        color_precision = self.config.get("color_precision", 6)
        filter_speckle = self.config.get("filter_speckle", 4)
        mode = self.config.get("mode", "spline")
        hierarchical = self.config.get("hierarchical", "cutout")
        min_region_area_mm2 = self.config.get("min_region_area_mm2", 2.0)
        min_boundary_length_mm = self.config.get("min_boundary_length_mm", 1.5)
        simplify_tolerance_mm = self.config.get("simplify_tolerance_mm", 0.15)
        wire_diameter_mm = self.config.get("wire_diameter_mm", 0.6)
        min_spacing_mm = self.config.get("min_wire_spacing_mm", 0.8)
        min_radius_mm = self.config.get("min_radius_mm", 1.0)
        smoothness = self.config.get("smoothness", 0.7)  # 0~1，越大越平滑
        gen_outline = self.config.get("gen_outline", False)

        self.output_width_mm = float(output_width_mm)

        # ========== Phase 1: VTracer 图片矢量化（复用开源） ==========
        self.vtracer = VTracerAdapter(
            color_precision=color_precision,
            filter_speckle=filter_speckle,
            mode=mode,
            hierarchical=hierarchical,
        )
        svg_raw = self.vtracer.convert(image_bytes, img_format)
        regions = self.vtracer.parse_regions()

        # 从VTracer输出确定图片尺寸和比例
        img_w, img_h = self.vtracer.width, self.vtracer.height
        scale = self.output_width_mm / img_w if img_w > 0 else 1.0
        self.output_height_mm = img_h * scale

        # ========== Phase 2: 区域处理（小区域过滤+邻接图） ==========
        # VTracer的label_map已经分好区域，用RegionSegmenter做后处理
        self.segmenter = RegionSegmenter(min_region_area_mm2=min_region_area_mm2, scale=scale)
        # 构建VTracer调色板（供RegionSegmenter使用）
        palette = []
        for r in regions:
            hex_color = r["color"]
            try:
                rgb = [int(hex_color[i:i+2], 16) for i in (1, 3, 5)]
            except ValueError:
                rgb = [0, 0, 0]
            palette.append({"id": r["id"], "hex": hex_color, "rgb": rgb})
        self.segmenter.segment(self.vtracer.label_map, palette)

        # ========== Phase 3: 公共边界提取（核心自研算法） ==========
        self.boundary_extractor = SharedBoundaryExtractor(
            scale=scale, min_boundary_length_mm=min_boundary_length_mm)
        self.boundary_extractor.extract(self.segmenter.regions, self.segmenter.label_map)

        # 外轮廓提取（规格书四十一章: 是否生成外轮廓）
        if gen_outline:
            self.boundary_extractor.extract_outline(self.segmenter.regions, self.segmenter.label_map)

        # ========== Phase 4: 曲线简化 + Bezier拟合 ==========
        # 平滑参数：smoothness 0~1，控制拟合容差（越大越平滑）
        # 平滑度70% → 容差0.15mm基准，平滑度100%→1.0mm，平滑度0%→0.05mm
        effective_tolerance = 0.05 + (simplify_tolerance_mm - 0.05) * (0.3 + 0.7 * smoothness)
        self.simplifier = CurveSimplifier(tolerance_mm=effective_tolerance)
        self.bezier_fitter = BezierFitter(max_error_mm=effective_tolerance)
        self.broken_repair = BrokenCurveRepair()

        curves = {}
        curve_list = []
        simplified_boundaries = []
        repair_records = []

        # 合并共享边界 + 外轮廓
        all_boundaries = list(self.boundary_extractor.boundaries)
        if gen_outline:
            all_boundaries += list(self.boundary_extractor.outline_boundaries)

        for b in all_boundaries:
            # 断线修复
            repaired = self.broken_repair.repair(b["points"])
            if repaired["repairs"]:
                repair_records.extend(repaired["repairs"])
            points_to_use = repaired["points"]

            simplified_points = self.simplifier.simplify(points_to_use)
            bezier_segments = self.bezier_fitter.fit(simplified_points)
            curves[b["id"]] = bezier_segments
            curve_list.append({
                "id": b["id"],
                "segments": bezier_segments,
                "closed": b["closed"],
                "boundary_ids": [b["id"]],
                "length_mm": b["length_mm"],
                "region_a": b["region_a"],
                "region_b": b["region_b"],
            })
            sb = dict(b)
            sb["points"] = simplified_points
            simplified_boundaries.append(sb)

        # ========== Phase 5: 曲线合并 + 工程验证 ==========
        broken_count = len([r for r in repair_records if r.get("type") in ("bezier_bridge", "auto_close")])

        self.curve_merger = CurveMerger(g0_tolerance_mm=0.01, g1_angle_deg=3.0)
        self.merged_curves = self.curve_merger.merge(curve_list)

        self.validator = CurveValidator(min_spacing_mm=min_spacing_mm, min_radius_mm=min_radius_mm)
        validation = self.validator.validate(self.merged_curves if self.merged_curves else curve_list)
        validation["broken_curve_count"] = broken_count
        validation["wire_diameter_mm"] = wire_diameter_mm
        validation["engine"] = "vtracer"
        # 规格书四十三章: 曲线检查面板数据
        validation["curve_group_count"] = len(self.merged_curves) if self.merged_curves else 0
        validation["outline_count"] = len(self.boundary_extractor.outline_boundaries) if gen_outline else 0
        # filtered短边界统计（小于min_boundary_length被过滤的数量）
        filtered_short = 0
        for b in self.boundary_extractor.boundaries:
            if b["length_mm"] < min_boundary_length_mm:
                filtered_short += 1
        validation["short_boundary_count"] = filtered_short

        try:
            boundary_graph = self.validator.build_boundary_graph(
                self.merged_curves if self.merged_curves else curve_list)
        except Exception:
            boundary_graph = {"nodes": [], "edges": []}

        # ========== Phase 6: 导出 ==========
        # SVG（含VTracer原始区域 + 掐丝线层）
        svg_exporter = SVGExporter(width_mm=self.output_width_mm, height_mm=self.output_height_mm)
        self.svg_content = svg_exporter.export(simplified_boundaries, curves)

        # DXF
        dxf_b64 = None
        try:
            dxf_exporter = DXFExporter()
            tmp_dxf = os.path.join(tempfile.gettempdir(), "cloisonne_curves.dxf")
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

        preview_images = self._generate_previews()

        merged_curves_data = []
        for mc in (self.merged_curves if self.merged_curves else []):
            merged_curves_data.append({
                "id": mc["id"],
                "boundary_ids": mc["boundary_ids"],
                "closed": mc["closed"],
                "segment_count": mc.get("segment_count", len(mc["segments"])),
                "length_mm": round(sum(self._seg_len(s) for s in mc["segments"]), 3),
            })

        self.result = {
            "image_info": {
                "width_px": img_w,
                "height_px": img_h,
                "output_width_mm": round(self.output_width_mm, 2),
                "output_height_mm": round(self.output_height_mm, 2),
                "scale_mm_per_px": round(scale, 6),
            },
            "engine": "vtracer",
            "color_palette": palette,
            "regions": self.segmenter.get_regions_info(),
            "boundaries": self.boundary_extractor.get_boundaries_info(),
            "curves": {
                bid: {
                    "segment_count": len(segs),
                    "segments": segs,
                }
                for bid, segs in curves.items()
            },
            "merged_curves": merged_curves_data,
            "boundary_graph": boundary_graph,
            "validation": validation,
            "svg": self.svg_content,
            "dxf_base64": dxf_b64,
            "ibl_text": ibl_text,
            "preview_images": preview_images,
            "repair_records": repair_records[:20],
            "config": {
                "smoothness": smoothness,
                "gen_outline": gen_outline,
            },
        }
        self.result = self._to_native(self.result)
        return self.result

    def _seg_len(self, seg):
        p0 = np.array(seg["p0"])
        p3 = np.array(seg["p3"])
        return float(np.linalg.norm(p3 - p0))

    @staticmethod
    def _to_native(obj):
        if isinstance(obj, dict):
            return {k: CloisonnePipeline._to_native(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [CloisonnePipeline._to_native(v) for v in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    def get_svg(self):
        return self.svg_content

    def get_dxf_bytes(self):
        dxf_exporter = DXFExporter()
        tmp_dxf = os.path.join(tempfile.gettempdir(), "cloisonne_curves.dxf")
        dxf_exporter.export(self.merged_curves if self.merged_curves else [], tmp_dxf)
        with open(tmp_dxf, "rb") as f:
            return f.read()

    def get_ibl_bytes(self):
        ibl_exporter = IBLExporter()
        tmp_ibl = os.path.join(tempfile.gettempdir(), "cloisonne_curves.ibl")
        ibl_exporter.export(self.merged_curves if self.merged_curves else [], tmp_ibl)
        with open(tmp_ibl, "rb") as f:
            return f.read()

    def _generate_previews(self):
        """生成预览图（base64 PNG）"""
        previews = {}
        h, w = self.vtracer.height, self.vtracer.width

        # 区域图（VTracer分色结果）
        region_img = self.vtracer.get_region_image()
        _, buffer = cv2.imencode(".png", cv2.cvtColor(region_img, cv2.COLOR_RGB2BGR))
        previews["regions"] = base64.b64encode(buffer).decode()

        # 边界图
        boundary_img = np.full((h, w, 3), 255, dtype=np.uint8)
        for b in self.boundary_extractor.boundaries:
            for px, py in b["points"]:
                x = int(px / self.boundary_extractor.scale)
                y = int(h - py / self.boundary_extractor.scale)
                if 0 <= x < w and 0 <= y < h:
                    cv2.circle(boundary_img, (x, y), 1, (0, 0, 0), -1)
        _, buffer = cv2.imencode(".png", cv2.cvtColor(boundary_img, cv2.COLOR_RGB2BGR))
        previews["boundaries"] = base64.b64encode(buffer).decode()

        return previews
