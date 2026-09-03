"""
VTracerAdapter - VTracer开源矢量化引擎适配器
规格书V2.0/V2.1:
- VTracer负责"图片→颜色区域→初始矢量曲线"，不重写
- 参数: colormode=color, hierarchical=cutout, mode=spline
- 从VTracer SVG中解析出颜色区域，生成label_map + Shapely Polygon
  （V2.1: 保留矢量几何，供Shared Boundary做Shapely矢量化，不再栅格化）
V2.3:
- 参数统一由 VTracerConfig 管理，本适配器不再接收散参
"""
import io
import re
import numpy as np
import cv2
import vtracer

from backend.segmentation.vtracer_config import VTracerConfig


class VTracerAdapter:
    def __init__(self, config=None, color_precision=6, filter_speckle=4,
                 mode="spline", hierarchical="cutout", colormode="color"):
        # V2.3: 优先接受 VTracerConfig；兼容旧散参调用
        if isinstance(config, VTracerConfig):
            self.config = config
        else:
            self.config = VTracerConfig(
                colormode=colormode,
                hierarchical=hierarchical,
                mode=mode,
                filter_speckle=filter_speckle,
                color_precision=color_precision,
            )
        self.svg = None
        self.regions = []       # [{id, color, path, segments, area_px, polygon, ...}]
        self.label_map = None   # (H, W) 每个像素的区域ID
        self.width = 0
        self.height = 0

    def convert(self, img_bytes, img_format="png"):
        """
        调用VTracer将图片转为SVG
        返回SVG字符串
        """
        self.svg = vtracer.convert_raw_image_to_svg(
            img_bytes,
            img_format=img_format,
            **self.config.to_vtracer_kwargs(),
        )
        # 从SVG中读取宽高
        m = re.search(r'width="(\d+)" height="(\d+)"', self.svg)
        if m:
            self.width = int(m.group(1))
            self.height = int(m.group(2))
        return self.svg

    def parse_regions(self):
        """
        用svgpathtools解析SVG中的path，建立颜色区域信息
        注意: VTracer会用transform="translate(...)"定位path，必须用文件方式
        让svgpathtools正确应用transform（StringIO方式会忽略transform）
        返回: regions列表 + label_map
        """
        import svgpathtools
        import tempfile
        import os

        # 写入临时文件以让svgpathtools正确处理transform
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w", encoding="utf-8") as tmp:
                tmp.write(self.svg)
                tmp_path = tmp.name
            paths, attributes = svgpathtools.svg2paths(tmp_path)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        self.regions = []
        for i, (path, attrs) in enumerate(zip(paths, attributes)):
            fill = attrs.get("fill", "#000000")
            # 清理颜色格式
            if fill.startswith("url("):
                fill = "#000000"
            if len(fill) == 4:  # 缩写 #RGB -> #RRGGBB
                fill = "#" + "".join(c * 2 for c in fill[1:])

            # 解析transform（VTracer用translate(tx,ty)定位path）
            tx, ty = self._parse_transform(attrs.get("transform", ""))

            # 采样path得到轮廓点，并应用transform偏移
            contour_pts = self._path_to_contour(path)
            if tx != 0 or ty != 0:
                contour_pts = contour_pts + np.array([tx, ty])
            if len(contour_pts) < 3:
                continue

            # 判断闭合
            closed = np.linalg.norm(contour_pts[0] - contour_pts[-1]) < 1.0

            # 计算面积（用闭合轮廓）
            area = self._contour_area(contour_pts)

            self.regions.append({
                "id": i,
                "color": fill,
                "path": path,
                "segments": list(path),
                "closed": bool(closed),
                "area_px": area,
                "contour_pts": contour_pts,
                "transform": [tx, ty],
                "polygon": self._build_polygon(path, (tx, ty)),
            })

        # 生成label_map：把每个path渲染到画布上
        self._build_label_map()
        return self.regions

    def _build_polygon(self, path, transform):
        """
        从svgpathtools path构造Shapely Polygon（应用transform偏移）
        V2.1: 保留VTracer矢量几何，供SharedBoundary做Shapely矢量化
        正确处理多子环（外环+孔洞，如背景区域）:
        面积法 - 最大子环为外环，其余子环为孔洞
        (不能用unary_union: 会把"带孔洞背景+花瓣面"合并成实心矩形, 孔洞丢失)
        """
        try:
            from shapely.geometry import Polygon, LineString
            from shapely.ops import unary_union
            from shapely.validation import make_valid
        except ImportError:
            return None

        tx, ty = transform
        rings = []
        # 分割为连续子路径（VTracer path可能含多个子环: 外环+孔洞）
        for sub in path.continuous_subpaths():
            pts = []
            for seg in sub:
                for i in range(20):  # 高密度采样
                    t = i / 20
                    pt = seg.point(t)
                    pts.append((float(pt.real) + tx, float(pt.imag) + ty))
            if len(pts) < 3:
                continue
            # 闭合环
            if abs(pts[0][0] - pts[-1][0]) > 1e-9 or abs(pts[0][1] - pts[-1][1]) > 1e-9:
                pts.append(pts[0])
            try:
                ring = LineString(pts)
                if ring.is_valid and ring.length > 1:
                    rings.append(ring)
            except Exception:
                continue

        if not rings:
            return None

        try:
            # 面积法: 最大环为外环, 其余为孔洞(或独立子多边形)
            rings.sort(key=lambda r: -r.length)
            outer = rings[0]
            holes = []
            extras = []
            for r in rings[1:]:
                try:
                    if outer.contains(r.representative_point()):
                        holes.append(r)
                    else:
                        extras.append(r)
                except Exception:
                    extras.append(r)
            poly = Polygon(outer.coords, [r.coords for r in holes])
            if extras:
                parts = [poly] + [Polygon(r.coords) for r in extras]
                poly = unary_union(parts)
            if not poly.is_valid:
                poly = make_valid(poly)
            if poly.is_empty:
                return None
            return poly
        except Exception:
            return None

    def _parse_transform(self, transform_str):
        """
        解析SVG transform字符串
        VTracer使用 translate(tx,ty) 格式，返回 (tx, ty)
        """
        if not transform_str:
            return (0.0, 0.0)
        import re
        m = re.search(r"translate\(\s*([-\d.]+)\s*[, ]\s*([-\d.]+)\s*\)", transform_str)
        if m:
            return (float(m.group(1)), float(m.group(2)))
        # 处理单参数 translate(tx)
        m = re.search(r"translate\(\s*([-\d.]+)\s*\)", transform_str)
        if m:
            return (float(m.group(1)), 0.0)
        return (0.0, 0.0)

    def _path_to_contour(self, path, samples_per_seg=5):
        """将svgpathtools path采样为轮廓点"""
        pts = []
        for seg in path:
            for i in range(samples_per_seg):
                t = i / samples_per_seg
                pt = seg.point(t)
                pts.append([float(pt.real), float(pt.imag)])
        return np.array(pts)

    def _contour_area(self, pts):
        """用鞋带公式计算多边形面积"""
        x = pts[:, 0]
        y = pts[:, 1]
        area = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        return float(area)

    def _build_label_map(self):
        """把每个区域渲染到画布，生成label_map
        使用已应用transform的contour_pts，避免fillPoly坐标错误"""
        h, w = self.height, self.width
        self.label_map = np.full((h, w), -1, dtype=np.int32)

        for region in self.regions:
            # 使用已应用transform的轮廓点
            pts = region["contour_pts"]
            # clip到画布内
            pts_clipped = np.clip(pts, 0, [w, h])
            poly = pts_clipped.astype(np.int32).reshape(-1, 1, 2)

            mask = np.zeros((h, w), dtype=np.uint8)
            try:
                cv2.fillPoly(mask, [poly], 255)
            except cv2.error:
                continue

            # 用该区域的ID填充label_map
            self.label_map[mask == 255] = region["id"]

        # 重新编号为连续ID（可能有空洞）
        unique_ids = np.unique(self.label_map[self.label_map >= 0])
        remap = {old: new for new, old in enumerate(sorted(unique_ids))}
        new_labels = np.full_like(self.label_map, -1)
        for old, new in remap.items():
            new_labels[self.label_map == old] = new
        self.label_map = new_labels

        # 更新区域ID
        for r in self.regions:
            r["id"] = int(remap.get(r["id"], r["id"]))

    def get_region_image(self):
        """生成区域着色预览图（RGB）"""
        h, w = self.height, self.width
        img = np.full((h, w, 3), 255, dtype=np.uint8)
        rng = np.random.RandomState(42)
        colors = rng.randint(50, 255, (len(self.regions), 3))
        for r in self.regions:
            img[self.label_map == r["id"]] = colors[r["id"] % len(colors)]
        return img

    def get_color_map(self):
        """返回每个颜色ID对应的RGB颜色（用于调色板）"""
        color_map = {}
        for r in self.regions:
            hex_color = r["color"]
            try:
                rgb = [int(hex_color[i:i+2], 16) for i in (1, 3, 5)]
            except ValueError:
                rgb = [0, 0, 0]
            color_map[r["id"]] = rgb
        return color_map
