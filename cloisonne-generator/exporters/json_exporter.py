"""
JSONExporter - 项目文件导出/加载模块
规格书第62章: 保存项目 / 加载项目，恢复图片、参数、区域、曲线、修改记录
规格书第35章: 最终数据模型 {version, image, settings, regions, boundaries, curves, validation}
"""
import json
import os
import base64


class JSONExporter:
    @staticmethod
    def export(project_data, filepath):
        """保存项目为JSON文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        return filepath

    @staticmethod
    def load(filepath):
        """加载项目JSON文件"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def build_project_data(result, filename="project"):
        """从管线结果构建项目数据模型（规格书第35章）"""
        return {
            "version": "1.0",
            "project_name": filename,
            "image": result.get("image_info", {}),
            "settings": {
                "color_count": len(result.get("color_palette", [])),
                "color_merge_delta_e": 8.0,
                "min_region_area_mm2": 2.0,
                "min_boundary_length_mm": 1.5,
                "wire_diameter_mm": 0.6,
                "min_wire_spacing_mm": 0.8,
                "min_radius_mm": 1.0,
                "simplify_tolerance_mm": 0.15,
                "smoothness": 0.7,
            },
            "color_palette": result.get("color_palette", []),
            "regions": result.get("regions", []),
            "boundaries": result.get("boundaries", []),
            "curves": result.get("curves", {}),
            "merged_curves": result.get("merged_curves", []),
            "validation": result.get("validation", {}),
        }
