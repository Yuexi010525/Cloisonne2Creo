"""
SVGExporter - SVG导出模块
规格书第41-43章:
- 优先Path，不用大量Polygon
- 使用Cubic Bezier
- 1 SVG unit = 1 mm
- 分层: regions / boundaries / final-wire-curves
"""
import numpy as np


class SVGExporter:
    def __init__(self, width_mm=100, height_mm=100):
        self.width_mm = width_mm
        self.height_mm = height_mm

    def export(self, boundaries, curves, regions=None, quantized_image_path=None):
        """
        生成完整SVG字符串
        boundaries: 公共边界列表（含points）
        curves: {boundary_id: [bezier_segments, ...]}
        regions: 区域信息（可选，用于填充色层）
        """
        svg_parts = []
        svg_parts.append(f'<?xml version="1.0" encoding="UTF-8"?>')
        svg_parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width_mm}mm" height="{self.height_mm}mm" '
            f'viewBox="0 0 {self.width_mm} {self.height_mm}" '
            f'version="1.1">'
        )

        # 样式定义
        svg_parts.append("""
  <defs>
    <style>
      .region-fill { fill-opacity: 0.3; stroke: none; }
      .boundary-raw { fill: none; stroke: #cccccc; stroke-width: 0.1; }
      .final-wire { fill: none; stroke: #d4af37; stroke-width: 0.3; stroke-linecap: round; stroke-linejoin: round; }
      .boundary-id { font-size: 1.5mm; fill: #666; font-family: sans-serif; }
    </style>
  </defs>
""")

        # Layer 1: 颜色区域填充（如果有）
        if regions:
            svg_parts.append('  <g id="regions">')
            for r in regions:
                if r.get("boundary_points"):
                    pts = " ".join([f"{p[0]},{p[1]}" for p in r["boundary_points"]])
                    svg_parts.append(f'    <polygon class="region-fill" points="{pts}" fill="{r["color"]}"/>')
            svg_parts.append('  </g>')

        # Layer 2: 原始边界（像素级折线，半透明灰色）
        svg_parts.append('  <g id="boundaries">')
        for b in boundaries:
            if len(b["points"]) >= 2:
                pts = " ".join([f"{p[0]},{p[1]}" for p in b["points"]])
                svg_parts.append(f'    <polyline class="boundary-raw" points="{pts}"/>')
        svg_parts.append('  </g>')

        # Layer 3: 最终掐丝曲线（贝塞尔，金色） — 独立分组，与 debug 标签分开
        svg_parts.append('  <g id="cloisonne-wire">')
        for b in boundaries:
            bid = b["id"]
            if bid in curves and curves[bid]:
                d = self._bezier_segments_to_path(curves[bid])
                if d:
                    svg_parts.append(f'    <path class="final-wire" d="{d}" id="{bid}"/>')
        svg_parts.append('  </g>')

        # Layer 4: Debug 标签（边界ID文本）— 默认隐藏，由前端"曲线编号"开关控制
        svg_parts.append('  <g id="debug-labels" style="display:none;">')
        for b in boundaries:
            bid = b["id"]
            if bid in curves and curves[bid] and len(b["points"]) >= 2:
                # 标注边界ID（中点位置）
                mid_idx = len(b["points"]) // 2
                mx, my = b["points"][mid_idx]
                svg_parts.append(f'    <text class="boundary-id" x="{mx}" y="{my}">{bid}</text>')
        svg_parts.append('  </g>')

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    def _bezier_segments_to_path(self, segments):
        """将贝塞尔段列表转为SVG path d字符串"""
        if not segments:
            return ""
        parts = [f"M {segments[0]['p0'][0]} {segments[0]['p0'][1]}"]
        for seg in segments:
            parts.append(
                f"C {seg['p1'][0]} {seg['p1'][1]}, "
                f"{seg['p2'][0]} {seg['p2'][1]}, "
                f"{seg['p3'][0]} {seg['p3'][1]}"
            )
        return " ".join(parts)

    def export_preview_svg(self, boundaries, curves):
        """仅导出最终曲线层（用于前端预览）"""
        return self.export(boundaries, curves, regions=None)
