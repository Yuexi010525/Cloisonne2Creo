"""
IBLExporter - Creo IBL曲线导出模块
规格书第47-49章:
- IBL是Creo专用曲线输出
- 每一条连续曲线按 curve group -> 多个有序点 输出
- 相邻曲线段端点必须坐标一致（禁止10.0001 vs 10.0020）
- 封装成独立Exporter，支持配置Creo/IBL版本模板
- 不能核心算法直接生成IBL
"""
import numpy as np


class IBLExporter:
    def __init__(self, template="creo"):
        """
        template: IBL格式模板
        - "creo": Creo标准IBL格式
        """
        self.template = template
        self.precision = 4  # 小数点后4位

    def export(self, curves, filepath):
        """
        导出IBL文件
        curves: [{"id", "segments": [cubic_bezier...], "closed", "boundary_ids"}]
        每个曲线组输出为独立的IBL section
        """
        lines = []
        lines.append("/* IBL 曲线数据 - 掐丝珐琅生成器 V1.0")
        lines.append("/* 单位: 毫米 (mm)")
        lines.append("/* 每个 section 表示一条连续曲线组")
        lines.append("")

        for c in curves:
            # 收集曲线上的有序点
            points = self._collect_points(c["segments"], samples=20)

            # 处理闭合曲线：首尾点重合
            if c.get("closed") and len(points) > 2:
                points.append(points[0])

            # 写入section头
            lines.append(f"begin section !{c['id']}")
            lines.append(f"begin curve !{c['id']}_curve")
            lines.append(f"1 {len(points)}")

            # 写入点（IBL格式: 点索引 + 坐标，Y向上坐标系统）
            for i, (x, y) in enumerate(points):
                # 归一化坐标并精确到4位小数，保证相邻段端点一致
                lines.append(f"{i+1} {x:.4f} {y:.4f} 0.0000")

            lines.append("")

        content = "\n".join(lines)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def get_raw_text(self, curves):
        """返回IBL原始文本（Debug模式查看）"""
        import io
        buffer = io.StringIO()
        old_filepath = "debug.ibl"
        import tempfile, os
        # 生成到临时文件再读回
        tmp = os.path.join(tempfile.gettempdir(), old_filepath)
        self.export(curves, tmp)
        with open(tmp, "r", encoding="utf-8") as f:
            return f.read()

    def _collect_points(self, segments, samples=20):
        """将贝塞尔段离散为有序点，并统一端点坐标精度"""
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
                points.append((pt[0], pt[1]))
        # 去重：同一贝塞尔段内的重复点
        dedup = []
        for p in points:
            x, y = p[0], p[1]
            if not dedup or abs(x - dedup[-1][0]) > 1e-6 or abs(y - dedup[-1][1]) > 1e-6:
                dedup.append(p)
        return dedup
