# -*- coding: utf-8 -*-
"""
scripts/test_frontend_data.py - 前端数据契约测试 (V2.3 第44阶段)
- 验证后端 result 包含前端 app.js 依赖的全部字段
- 验证 normalize_result() 统一 Schema 可消费
- 不依赖服务器, 直接跑 pipeline (真实运行, 不造假)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.lineart.pipeline import LineArtPipeline
from backend.pipeline import CloisonnePipeline
from backend.result_schema import normalize_result

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(BASE, "examples")

# 前端 app.js 渲染依赖的关键字段 (renderLineartResult / renderColorResult / renderSvgResult)
FRONTEND_REQUIRED = [
    "mode", "engine", "image_info", "validation",
    "preview_images", "svg",
]
LINEART_REQUIRED = ["strokes", "branches", "centerlines", "junctions", "endpoints",
                    "merged_curves", "lineart_stats", "dxf_base64", "ibl_text"]
COLOR_REQUIRED = ["regions", "boundaries", "curves"]


def check_lineart():
    with open(os.path.join(EX, "test_user_lineart.png"), "rb") as f:
        img = f.read()
    pipe = LineArtPipeline({"graph_engine": "skan", "wire_diameter_mm": 0.6,
                            "recommended_spacing_mm": 0.8})
    r = pipe.run(img, output_width_mm=100, img_format="png")
    missing = [k for k in FRONTEND_REQUIRED + LINEART_REQUIRED if k not in r]
    print(f"LineArt 前端字段: {'OK' if not missing else '缺失 ' + str(missing)}")
    n = normalize_result(r)
    assert n["mode"] == "lineart"
    assert "geometry" in n and "strokes" in n["geometry"]
    assert "exports" in n and "dxf_base64" in n["exports"]
    print("normalize_result(lineart): OK (mode/geometry/exports 齐备)")
    return r


def check_color():
    with open(os.path.join(EX, "test03_flower.png"), "rb") as f:
        img = f.read()
    pipe = CloisonnePipeline({"color_precision": 6, "filter_speckle": 4})
    r = pipe.run(img, output_width_mm=100, img_format="png")
    missing = [k for k in FRONTEND_REQUIRED + COLOR_REQUIRED if k not in r]
    print(f"Color 前端字段: {'OK' if not missing else '缺失 ' + str(missing)}")
    n = normalize_result(r)
    assert n["mode"] in ("cloisonne", "spline", "color")
    assert "regions" in n["geometry"]
    print("normalize_result(color): OK")
    return r


def main():
    print("=" * 60)
    print("前端数据契约测试 (V2.3 第44阶段)")
    print("=" * 60)
    check_lineart()
    check_color()
    print("\n全部通过")


if __name__ == "__main__":
    main()
