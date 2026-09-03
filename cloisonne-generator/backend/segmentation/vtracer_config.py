# -*- coding: utf-8 -*-
"""
VTracerConfig - VTracer 参数统一管理 (V2.3)
规格书(V2.3 第6-8阶段):
  - VTracer 负责 Image → Vector (color / bw / spline / simplify)
  - 参数集中管理, 不让散落在多个 Python 文件
  - 彩色模式默认: clustering=color-cluster, hierarchical=cutout, mode=spline, filter_speckle=4
  - 线稿模式默认: clustering=bw, mode=spline, filter_speckle=4, binary_threshold=128, adaptive=False
  - 建立 px_to_mm() / mm_to_px() 统一换算, 不要把像素参数直接当毫米参数

注意: 当前安装 vtracer 0.6.15 实际支持 convert_raw_image_to_svg 的参数为:
  colormode / hierarchical / mode / filter_speckle / color_precision /
  layer_difference / corner_threshold / length_threshold / max_iterations /
  splice_threshold / path_precision
规格书中 Config.bw() 等 preset 属于更新开发线 API, 此处以当前版本能力为准,
保留规格书参数作为配置字段并标注 supported=False。
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any


# =====================================================================
# px / mm 换算工具 (统一入口, 规格书第7阶段)
# =====================================================================
def px_to_mm(px: float, output_width_mm: float, image_width_px: float) -> float:
    """像素 → 毫米. output_width_mm 是期望的成品宽度(mm), image_width_px 是输入图宽(px)"""
    if not image_width_px:
        return 0.0
    return float(px) * float(output_width_mm) / float(image_width_px)


def mm_to_px(mm: float, output_width_mm: float, image_width_px: float) -> float:
    """毫米 → 像素"""
    if not output_width_mm:
        return 0.0
    return float(mm) * float(image_width_px) / float(output_width_mm)


# =====================================================================
# VTracerConfig
# =====================================================================
@dataclass
class VTracerConfig:
    # ---- 当前 vtracer 0.6.15 实际支持的参数 ----
    colormode: str = "color"        # color / bw (对应规格书 clustering)
    hierarchical: str = "cutout"    # cutout / stacked
    mode: str = "spline"            # spline / polygon / none
    filter_speckle: int = 4
    color_precision: int = 6
    layer_difference: int = 16
    corner_threshold: float = 60
    length_threshold: float = 4.0
    max_iterations: int = 10
    splice_threshold: float = 45
    path_precision: int = 8

    # ---- 规格书参数 (当前 0.6.15 不支持, 保留为配置字段) ----
    # simplify 等由 mode=spline 隐含; binary_threshold 由线稿模式自行处理
    simplify: Optional[float] = None            # supported=False (0.6.15)
    binary_threshold: Optional[int] = None      # supported=False (0.6.15 需由 OpenCV 处理)
    adaptive: bool = False                      # supported=False (0.6.15)
    adaptive_window: int = 50                   # supported=False (0.6.15)
    adaptive_t: float = 8.0                     # supported=False (0.6.15)
    max_colors: Optional[int] = None            # supported=False (0.6.15)
    palette: Optional[list] = None              # supported=False (0.6.15)
    optimize: bool = False                      # supported=False (0.6.15)

    @classmethod
    def color_preset(cls, color_precision: int = 6, filter_speckle: int = 4) -> "VTracerConfig":
        """彩色模式默认配置 (规格书第7阶段)"""
        return cls(
            colormode="color",
            hierarchical="cutout",
            mode="spline",
            filter_speckle=filter_speckle,
            color_precision=color_precision,
        )

    @classmethod
    def lineart_preset(cls, filter_speckle: int = 4,
                       binary_threshold: Optional[int] = 128) -> "VTracerConfig":
        """线稿模式默认配置 (规格书第8阶段)"""
        return cls(
            colormode="bw",
            hierarchical="cutout",
            mode="spline",
            filter_speckle=filter_speckle,
            color_precision=6,
            binary_threshold=binary_threshold,
        )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VTracerConfig":
        """从 dict 构建 (仅取已知字段, 忽略未知)"""
        known = {f: d[f] for f in asdict(cls()) if f in d}
        return cls(**known)

    def to_vtracer_kwargs(self) -> Dict[str, Any]:
        """转为 vtracer.convert_raw_image_to_svg 支持的参数 (0.6.15)"""
        return {
            "colormode": self.colormode,
            "hierarchical": self.hierarchical,
            "mode": self.mode,
            "filter_speckle": self.filter_speckle,
            "color_precision": self.color_precision,
            "layer_difference": self.layer_difference,
            "corner_threshold": self.corner_threshold,
            "length_threshold": self.length_threshold,
            "max_iterations": self.max_iterations,
            "splice_threshold": self.splice_threshold,
            "path_precision": self.path_precision,
        }

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # 标注规格书字段在当前版本的支持状态
        unsupported = ["simplify", "binary_threshold", "adaptive", "adaptive_window",
                       "adaptive_t", "max_colors", "palette", "optimize"]
        for k in unsupported:
            d[k] = {"value": d[k], "supported": False}
        return d
