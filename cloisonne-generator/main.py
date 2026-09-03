"""
FastAPI 主入口
规格书第65章: API建议
POST /api/upload, /api/analyze, /api/export/svg, ...
"""
import sys
import os
import json
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.pipeline import CloisonnePipeline

app = FastAPI(title="掐丝珐琅图片转Creo曲线生成器 V1.0", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局缓存当前处理结果
current_result = None
current_config = {}
current_pipeline = None

# 静态文件服务
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>掐丝珐琅生成器 V1.0</h1><p>前端文件未找到</p>"


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    color_count: int = Form(0),
    color_precision: int = Form(6),
    filter_speckle: int = Form(4),
    mode: str = Form("spline"),
    hierarchical: str = Form("cutout"),
    color_merge_delta_e: float = Form(8.0),
    min_region_area_mm2: float = Form(2.0),
    min_boundary_length_mm: float = Form(1.5),
    simplify_tolerance_mm: float = Form(0.15),
    wire_diameter_mm: float = Form(0.6),
    min_wire_spacing_mm: float = Form(0.8),
    recommended_spacing_mm: float = Form(0.8),
    min_radius_mm: float = Form(1.0),
    output_width_mm: float = Form(100.0),
    generate_mode: str = Form("cloisonne"),
    gen_mode: str = Form(""),
    smoothness: float = Form(0.7),
    gen_outline: bool = Form(False),
    # V2.2 线稿参数
    binary_threshold: str = Form(""),
    denoise_ksize: int = Form(3),
    min_spur_length_mm: float = Form(0.8),
    keep_fine_segments: bool = Form(False),
    skeleton_method: str = Form("skeletonize"),
    graph_engine: str = Form("skan"),
):
    """V2.2分析管线
    gen_mode: auto(自动检测) / cloisonne(彩色掐丝) / lineart(黑白线稿) / svg / outline
    兼容旧参数 generate_mode"""
    global current_result, current_config, current_pipeline

    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="上传文件为空")

        # VTracer 0.6.15 bug: color_precision=9 导致整图只输出1个颜色，映射到10
        if color_precision == 9:
            color_precision = 10

        # 兼容新旧参数名
        effective_mode = gen_mode if gen_mode else generate_mode
        effective_spacing = recommended_spacing_mm if recommended_spacing_mm > 0 else min_wire_spacing_mm

        config = {
            "color_precision": max(1, min(12, color_precision)),
            "filter_speckle": max(0, min(20, filter_speckle)),
            "mode": mode if mode in ("spline", "polygon", "none") else "spline",
            "hierarchical": hierarchical if hierarchical in ("cutout", "stacked") else "cutout",
            "min_region_area_mm2": max(0.1, min_region_area_mm2),
            "min_boundary_length_mm": max(0.5, min_boundary_length_mm),
            "simplify_tolerance_mm": max(0.05, min(1.0, simplify_tolerance_mm)),
            "wire_diameter_mm": max(0.2, min(2.0, wire_diameter_mm)),
            "recommended_spacing_mm": max(0.2, effective_spacing),
            "min_wire_spacing_mm": max(0.2, effective_spacing),
            "min_radius_mm": max(0.1, min_radius_mm),
            "smoothness": max(0.0, min(1.0, smoothness)),
            "gen_outline": bool(gen_outline),
            # V2.2 线稿参数
            "binary_threshold": int(binary_threshold) if binary_threshold and binary_threshold != "auto" else None,
            "denoise_ksize": max(0, min(9, denoise_ksize)),
            "min_spur_length_mm": max(0.2, min_spur_length_mm),
            "keep_fine_segments": bool(keep_fine_segments),
            "skeleton_method": skeleton_method,
            "graph_engine": graph_engine if graph_engine in ("skan", "legacy") else "skan",
        }
        current_config = config

        # 根据生成模式处理
        if effective_mode == "svg":
            # 普通SVG模式：直接返回VTracer原始SVG
            from backend.segmentation.vtracer_adapter import VTracerAdapter
            adapter = VTracerAdapter(
                color_precision=config["color_precision"],
                filter_speckle=config["filter_speckle"],
                mode=config["mode"],
                hierarchical=config["hierarchical"],
            )
            svg_raw = adapter.convert(image_bytes, _detect_format(file.filename))
            current_pipeline = adapter
            return JSONResponse(content={
                "engine": "vtracer-svg",
                "mode": "svg",
                "svg": svg_raw,
                "image_info": {
                    "width_px": adapter.width,
                    "height_px": adapter.height,
                    "output_width_mm": output_width_mm,
                },
            })

        if effective_mode == "outline":
            # 仅轮廓模式：VTracer用none模式只输出轮廓线
            from backend.segmentation.vtracer_adapter import VTracerAdapter
            adapter = VTracerAdapter(
                color_precision=config["color_precision"],
                filter_speckle=config["filter_speckle"],
                mode="none",
                hierarchical="cutout",
            )
            svg_raw = adapter.convert(image_bytes, _detect_format(file.filename))
            current_pipeline = adapter
            return JSONResponse(content={
                "engine": "vtracer-outline",
                "mode": "outline",
                "svg": svg_raw,
                "image_info": {
                    "width_px": adapter.width,
                    "height_px": adapter.height,
                    "output_width_mm": output_width_mm,
                },
            })

        # V2.2 线稿模式 / 自动检测
        if effective_mode in ("lineart", "auto"):
            from backend.lineart.pipeline import LineArtPipeline
            from backend.lineart.detector import LineArtDetector
            auto_detection = None
            if effective_mode == "auto":
                # 先解码图像用于检测
                import numpy as np
                import cv2
                nparr = np.frombuffer(image_bytes, np.uint8)
                img_bgr_auto = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                detector = LineArtDetector()
                det_result = detector.detect(img_bgr_auto)
                is_lineart = (det_result.get("mode") == "lineart")
                auto_detection = det_result
                if not is_lineart:
                    # 自动检测为彩色图，走掐丝模式
                    pipeline = CloisonnePipeline(config)
                    current_pipeline = pipeline
                    result = pipeline.run(image_bytes, output_width_mm=output_width_mm, img_format=_detect_format(file.filename))
                    current_result = result
                    summary = {
                        "engine": result["engine"],
                        "mode": "cloisonne",
                        "auto_detection": auto_detection,
                        "image_info": result["image_info"],
                        "color_palette": result["color_palette"],
                        "regions": result["regions"],
                        "boundaries": result["boundaries"],
                        "curves_summary": {
                            bid: {"segment_count": v["segment_count"]}
                            for bid, v in result["curves"].items()
                        },
                        "merged_curves": result["merged_curves"],
                        "validation": result["validation"],
                        "preview_images": result["preview_images"],
                        "has_dxf": result.get("dxf_base64") is not None,
                        "has_ibl": result.get("ibl_text") is not None,
                    }
                    return JSONResponse(content=summary)

            # 线稿模式
            la_pipeline = LineArtPipeline(config)
            current_pipeline = la_pipeline
            result = la_pipeline.run(image_bytes, output_width_mm=output_width_mm, img_format=_detect_format(file.filename))
            current_result = result
            summary = {
                "engine": result.get("engine", "lineart_skeleton"),
                "mode": "lineart",
                "auto_detection": auto_detection,
                "image_info": result["image_info"],
                "lineart_stats": result.get("lineart_stats", {}),
                "strokes": result.get("strokes", []),
                "branches": result.get("branches", []),
                "centerlines": {
                    cid: {"segment_count": len(v.get("segments", [])), "length_mm": v.get("length_mm", 0)}
                    for cid, v in result.get("centerlines", {}).items()
                },
                "junctions": result.get("junctions", []),
                "endpoints": result.get("endpoints", []),
                "merged_curves": result.get("merged_curves", []),
                "validation": result["validation"],
                "preview_images": result.get("preview_images", {}),
                "dxf_base64": result.get("dxf_base64"),
                "ibl_text": result.get("ibl_text"),
            }
            return JSONResponse(content=summary)

        # 掐丝珐琅模式（默认）：完整管线
        pipeline = CloisonnePipeline(config)
        current_pipeline = pipeline
        result = pipeline.run(image_bytes, output_width_mm=output_width_mm, img_format=_detect_format(file.filename))
        current_result = result

        # 返回不含大字段的摘要
        summary = {
            "engine": result["engine"],
            "image_info": result["image_info"],
            "color_palette": result["color_palette"],
            "regions": result["regions"],
            "boundaries": result["boundaries"],
            "curves_summary": {
                bid: {"segment_count": v["segment_count"]}
                for bid, v in result["curves"].items()
            },
            "merged_curves": result["merged_curves"],
            "validation": result["validation"],
            "preview_images": result["preview_images"],
            "has_dxf": result.get("dxf_base64") is not None,
            "has_ibl": result.get("ibl_text") is not None,
        }
        return JSONResponse(content=summary)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _detect_format(filename):
    """根据文件名推断图片格式"""
    if not filename:
        return "png"
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext in ("jpg", "jpeg"):
        return "jpeg"
    return ext if ext in ("png", "webp", "bmp") else "png"


@app.get("/api/svg")
async def get_svg():
    """获取当前分析结果的SVG"""
    if current_pipeline is None:
        raise HTTPException(status_code=404, detail="请先上传图片并分析")
    if isinstance(current_pipeline, CloisonnePipeline):
        svg = current_pipeline.get_svg()
    elif hasattr(current_pipeline, "svg"):
        svg = current_pipeline.svg
    else:
        raise HTTPException(status_code=404, detail="当前模式无SVG")
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/api/download/svg")
async def download_svg():
    """下载SVG文件"""
    if current_pipeline is None:
        raise HTTPException(status_code=404, detail="请先上传图片并分析")
    if isinstance(current_pipeline, CloisonnePipeline):
        svg = current_pipeline.get_svg()
    elif hasattr(current_pipeline, "svg"):
        svg = current_pipeline.svg
    else:
        raise HTTPException(status_code=404, detail="当前模式无SVG")
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Content-Disposition": "attachment; filename=cloisonne_curves.svg"}
    )


@app.get("/api/result")
async def get_full_result():
    """获取完整结果（含曲线数据）"""
    if current_result is None:
        raise HTTPException(status_code=404, detail="请先上传图片并分析")
    # 不含预览图（太大）
    return {
        "image_info": current_result["image_info"],
        "color_palette": current_result["color_palette"],
        "regions": current_result["regions"],
        "boundaries": current_result["boundaries"],
        "curves": current_result["curves"],
        "validation": current_result["validation"],
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/download/dxf")
async def download_dxf():
    """下载DXF文件（Creo通用CAD格式）"""
    if current_result is None:
        raise HTTPException(status_code=404, detail="请先上传图片并分析")
    try:
        from backend.pipeline import CloisonnePipeline
        dxf_bytes = current_pipeline.get_dxf_bytes()
        return Response(
            content=dxf_bytes,
            media_type="application/dxf",
            headers={"Content-Disposition": "attachment; filename=cloisonne_curves.dxf"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"DXF导出失败: {str(e)}")


@app.get("/api/download/ibl")
async def download_ibl():
    """下载IBL文件（Creo专用基准曲线）"""
    if current_result is None:
        raise HTTPException(status_code=404, detail="请先上传图片并分析")
    try:
        ibl_bytes = current_pipeline.get_ibl_bytes()
        return Response(
            content=ibl_bytes,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=cloisonne_curves.ibl"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"IBL导出失败: {str(e)}")


@app.get("/api/download/json")
async def download_json():
    """下载JSON项目文件"""
    if current_result is None:
        raise HTTPException(status_code=404, detail="请先上传图片并分析")
    try:
        from exporters.json_exporter import JSONExporter
        project_data = JSONExporter.build_project_data(current_result)
        return Response(
            content=json.dumps(project_data, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=cloisonne_project.json"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"JSON导出失败: {str(e)}")


@app.get("/api/debug/ibl")
async def debug_ibl():
    """查看IBL原始文本（Debug模式）"""
    if current_result is None:
        raise HTTPException(status_code=404, detail="请先上传图片并分析")
    ibl_text = current_result.get("ibl_text", "无IBL数据")
    return Response(content=ibl_text, media_type="text/plain")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
