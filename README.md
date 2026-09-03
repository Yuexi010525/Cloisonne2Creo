# 掐丝珐琅图片转 Creo 曲线生成器（Cloisonne2Creo）

把图片转换为可直接进 Creo 的掐丝珐琅中心线（SVG / DXF / IBL / JSON）的工具。

> 本仓库由开发者 + AI 协作开发。开发过程中使用了 OpenAI ChatGPT 输出的技术规格书（见 `docs/`），当前实现严格遵循 V2.1 规格书：**不重复造轮子，几何正确优先，输入语义分叉**——彩色填充图复用开源 VTracer 做矢量化引擎、Shapely 做矢量几何（Region→SharedBoundary）；黑白线稿复用 scikit-image 做骨架化（Stroke→Skeleton 中心线），彻底解决粗线变双线问题。自动检测输入类型，不确定时优先彩色模式。

## 快速开始

```bash
cd cloisonne-generator
# 方式1：双击 start.bat（自动检测Python 3.12并启动）
# 方式2：手动
C:\Users\<你的用户名>\AppData\Local\Programs\Python\Python312\python.exe main.py
# 浏览器打开 http://127.0.0.1:8765
```

依赖：见 `cloisonne-generator/requirements.txt`（fastapi, uvicorn, opencv-python, numpy, svgpathtools, ezdxf, vtracer, shapely, scikit-image, Pillow, python-multipart）

## 目录结构

```
docs/                     ChatGPT 导出的技术规格书（V1.0 + V2.0 + V2.1）
测试图片/                 用户原始掐丝线稿素材（源流之子系列）
cloisonne-generator/
  backend/                V2.1 管线
    lineart/              V2.1 新增：线稿模式（detector/preprocess/skeleton/graph/pruning/pipeline）
    boundary/             Shapely共享边界提取
    curve/                简化/Bezier拟合/合并/断线修复
    segmentation/         VTracer适配/区域分割
    validation/           工程验证（自交/线距/小半径）
    legacy/               已废弃模块（quantizer/processor）
  frontend/               Web 界面（参数预设 / 曲线检查面板 / 颜色交互）
  exporters/              SVG / DXF / IBL / JSON 导出器
  tests/                  验收测试 + 多轮结果生成脚本
  examples/               测试图 + 输出样例
  results/                6 轮生成结果（result.json + preview.svg）
  main.py / start.bat / requirements.txt / README.md
```

## 架构（V2.1 复用 vs 自研）

| 环节 | 方案 | 说明 |
|------|------|------|
| 图片矢量化 | **复用 VTracer** (MIT) | `convert_raw_image_to_svg`, colormode=color / hierarchical=cutout / mode=spline |
| SVG 解析 | **复用 svgpathtools** (MIT) | 解析 VTracer 输出的 path |
| 矢量几何 | **复用 Shapely** (BSD-3) | V2.1 核心：共享边界 buffer 容差交 / 自交 is_simple / 线距 distance |
| Shared Boundary | **自研** | 从 VTracer 区域邻接关系提取共享边界中心线（纯矢量几何） |
| 工程约束 | **自研** | 断线修复 / G0/G1 连续性(4端点自动翻转) / 线距冲突 / 小半径检测 |
| Creo 导出 | **自研** | SVG / DXF(SPLINE) / IBL(4位小数坐标) / JSON |

## 6 轮生成结果速览（results/）

| 轮次 | 图 | 区域 | 边界 | 状态 | 特点 |
|------|----|------|------|------|------|
| R01 | test01 两色块 | 2 | 1 | ok | 基础验证 |
| R02 | test03 花朵·普通 | 14 | 20 | warning | 默认参数 |
| R03 | test03 花朵·高精度 | 14 | 20 | warning | color_precision=12 + 外轮廓 |
| R04 | test03 花朵·快速预览 | 14 | 20 | warning | 低精度快出 |
| R05 | test04 卡通猫·外轮廓 | 15 | 21 | warning | 含外轮廓 |
| R06 | test02 三色块·SVG模式 | 4 | 5 | warning | 彩色SVG直出 |

详细指标与参数见 `cloisonne-generator/results/RESULTS_SUMMARY.md`

## 许可证

- 本项目代码：MIT（见 cloisonne-generator README）
- VTracer / image-to-svg / svgpathtools / ezdxf / Shapely：MIT / BSD-3
- Lumina-Layers：GPL-3.0（仅参考算法思路，不复制源码）
