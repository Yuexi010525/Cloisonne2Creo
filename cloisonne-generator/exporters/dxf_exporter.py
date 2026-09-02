"""
DXFExporter - DXF导出模块
规格书第44-46章:
- 使用ezdxf
- 优先输出SPLINE或LWPOLYLINE
- 如果可以Spline实现，优先Spline
- 避免几百个LINE模拟一条曲线
- 单位毫米，1 unit = 1 mm
- 图层: CLOISONNE_WIRE / CLOISONNE_OUTLINE / CLOISONNE_DEBUG
"""
import numpy as np


class DXFExporter:
    def __init__(self):
        self.layer_wire = "CLOISONNE_WIRE"
        self.layer_outline = "CLOISONNE_OUTLINE"
        self.layer_debug = "CLOISONNE_DEBUG"

    def export(self, curves, filepath, closed_curves=None):
        """
        导出DXF文件
        curves: [{"id", "segments": [cubic_bezier...], "closed"}]
        closed_curves: 需要闭合的曲线ID列表（可选）
        """
        import ezdxf

        doc = ezdxf.new("R2010")
        doc.units = ezdxf.units.MM

        # 创建图层
        for layer in [self.layer_wire, self.layer_outline, self.layer_debug]:
            doc.layers.add(layer)

        msp = doc.modelspace()

        for c in curves:
            # 将贝塞尔段转换为SPLINE控制点
            spline_pts = self._beziers_to_spline_points(c["segments"], samples=15)
            if len(spline_pts) < 2:
                continue

            # 创建SPLINE实体（用拟合点方式，保证平滑）
            if len(spline_pts) >= 3:
                spline = msp.add_spline(
                    fit_points=spline_pts,
                    degree=3,
                    dxfattribs={"layer": self.layer_wire}
                )
                if c.get("closed"):
                    spline.closed = True
            else:
                # 两点退化为直线
                msp.add_line(
                    spline_pts[0], spline_pts[1],
                    dxfattribs={"layer": self.layer_wire}
                )

        doc.saveas(filepath)
        return filepath

    def _beziers_to_spline_points(self, segments, samples=15):
        """将多个贝塞尔段离散为样条拟合点"""
        points = []
        for seg in segments:
            p0 = np.array(seg["p0"])
            p1 = np.array(seg["p1"])
            p2 = np.array(seg["p2"])
            p3 = np.array(seg["p3"])
            for i in range(samples):
                t = i / samples
                mt = 1 - t
                pt = (mt**3 * p0 + 3*mt**2*t * p1 + 3*mt*t**2 * p2 + t**3 * p3)
                points.append((float(pt[0]), float(pt[1])))
            if len(points) > samples:  # 每段结束处会重复，去掉重复点
                points = points[:-1]
        # 补最后一段终点
        last = segments[-1]
        points.append((float(last["p3"][0]), float(last["p3"][1])))
        return points
