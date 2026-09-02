# 掐丝珐琅图片转 Creo 曲线生成器 V2.0 (Cloisonne2Creo)

> **V2.0 核心原则：不重复造轮子**
> 矢量化引擎复用开源项目 **VTracer**，只开发项目特有的 **Shared Boundary** + **工程约束** + **Creo 导出**。

## 架构

```
图片
 │
 ▼
┌────────────────────────────────────────────────┐
│  VTracer (开源矢量化引擎，pip install vtracer)  │
│  图片 → 颜色区域 → 初始Spline矢量曲线            │
│  参数: colormode=color, hierarchical=cutout,   │
│        mode=spline, filter-speckle,            │
│        color-precision                         │
└────────────────────────────────────────────────┘
 │ SVG解析 (svgpathtools) → label_map
 ▼
┌────────────────────────────────────────────────┐
│  【项目特有】Shared Boundary 提取               │
│  相邻颜色区域的公共边界（非各自轮廓叠加）         │
└────────────────────────────────────────────────┘
 │
 ▼
┌────────────────────────────────────────────────┐
│  工程验证 (CurveValidator)                      │
│  最小间距 / 最小曲率半径 / 自交 / 断线修复       │
│  曲线合并 (G0/G1连续性)                        │
└────────────────────────────────────────────────┘
 │
 ▼
┌────────────────────────────────────────────────┐
│  导出                                       │
│  SVG (1unit=1mm) / DXF (SPLINE) /            │
│  IBL (Creo专用) / JSON (项目文件)              │
└────────────────────────────────────────────────┘
```

## 快速开始

### 方式一：双击启动（推荐）

```
双击 start.bat
```

自动安装依赖、启动服务器并打开浏览器。

### 方式二：命令行启动

```bash
pip install -r requirements.txt
python main.py
```

然后访问 http://127.0.0.1:8765

## 生成模式

前端提供三种生成模式：

| 模式 | 说明 | 输出 |
|------|------|------|
| **掐丝珐琅** (默认) | 完整管线：VTracer分色 → Shared Boundary → 工程验证 → Creo导出 | 掐丝线 + DXF/IBL |
| **普通SVG** | 仅 VTracer 彩色矢量化，不做掐丝处理 | 彩色SVG |
| **仅轮廓** | 仅输出轮廓线 | 轮廓SVG |

## 参数预设模板

| 模板 | 适用场景 | 参数特点 |
|------|---------|---------|
| **普通花纹** | 默认，均衡 | 颜色精度6 / 斑点4 / 简化0.15mm |
| **高精度细节** | 小细节、眼睛、花纹 | 颜色精度9 / 斑点2 / 简化0.08mm / 最小区域0.5mm² |
| **快速预览** | 快速出效果 | 颜色精度4 / 斑点8 / 简化0.25mm / 最小区域4mm² |

## 曲线检查面板（规格书四十三章）

生成后实时显示：
```
区域数 | 边界数 | 连续曲线组
短边界 | 断线 | 自交 | 线距冲突 | 小半径
```

## 颜色交互（规格书四十五章）

点击左侧调色板的颜色，高亮对应区域，显示：
- 该颜色区域的共享边界总数
- 相邻区域列表及各自共享边界数量

## 参数说明

### VTracer 参数（颜色处理）
| 参数 | 默认 | 范围 | 说明 |
|------|------|------|------|
| 颜色精度 color-precision | 6 | 1~12 | 值越高颜色区分越细 |
| 斑点过滤 filter-speckle | 4 | 0~20 | 值越高过滤越强，去除小噪点 |
| 分区模式 hierarchical | cutout | cutout/stacked | cutout=无缝分区，stacked=叠加 |
| 曲线模式 mode | spline | spline/polygon | spline=平滑曲线，polygon=多边形 |

### 工程参数
| 参数 | 默认 | 说明 |
|------|------|------|
| 输出宽度 (mm) | 100 | 最终CAD尺寸 |
| 线径 (mm) | 0.6 | 掐丝金属丝直径 |
| 最小线间距 (mm) | 0.8 | 过密区域检测 |
| 最小区域面积 (mm²) | 2.0 | 小区域合并阈值 |
| 最小边界长度 (mm) | 1.5 | 过短边界过滤 |
| 曲线简化容差 (mm) | 0.15 | Douglas-Peucker |
| 最小曲率半径 (mm) | 1.0 | 过急弯检测 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analyze` | 上传图片并分析（支持三种模式） |
| GET | `/api/svg` | 获取当前结果的 SVG |
| GET | `/api/download/svg` | 下载 SVG 文件 |
| GET | `/api/download/dxf` | 下载 DXF 文件（SPLINE） |
| GET | `/api/download/ibl` | 下载 IBL 文件（Creo 专用） |
| GET | `/api/download/json` | 下载 JSON 项目文件 |
| GET | `/api/debug/ibl` | 查看 IBL 原始文本 |
| GET | `/api/result` | 获取完整结果数据 |
| GET | `/api/health` | 健康检查 |

## 项目结构

```
cloisonne-generator/
├── main.py                        # FastAPI 入口
├── start.bat                      # Windows 启动脚本
├── requirements.txt               # 依赖清单（含vtracer, ezdxf）
├── frontend/
│   ├── index.html                 # 主界面（三种模式 + 参数区）
│   ├── css/style.css
│   └── js/app.js
├── backend/
│   ├── pipeline.py                # V2.0管线（VTracer引擎）
│   ├── segmentation/
│   │   ├── vtracer_adapter.py     # 【复用开源】VTracer适配器
│   │   └── region_segmenter.py    # 【自研】区域分割+邻接图
│   ├── boundary/
│   │   └── shared_boundary.py     # 【自研·核心】公共边界提取
│   ├── curve/
│   │   ├── simplifier.py          # 【自研】Douglas-Peucker简化
│   │   ├── bezier_fitter.py       # 【自研】三次贝塞尔拟合
│   │   ├── curve_merger.py        # 【自研】G0/G1连续性+曲线合并
│   │   └── broken_repair.py       # 【自研】断线检测与修复
│   └── validation/
│       └── curve_validator.py     # 【自研】间距/半径/自交/拓扑验证
├── exporters/
│   ├── svg_exporter.py            # 【自研】SVG导出
│   ├── dxf_exporter.py            # 【自研】DXF导出 (SPLINE)
│   ├── ibl_exporter.py            # 【自研】IBL (Creo) 导出
│   └── json_exporter.py           # 【自研】JSON项目文件
├── tests/
│   ├── test_v2_pipeline.py        # V2.0管线测试
│   ├── test_vtracer_adapter.py    # VTracer适配器测试
│   └── test_exports.py            # 导出验证
└── examples/test_pattern.png      # 测试图
```

## 复用 vs 自研对照

| 功能 | 来源 | 说明 |
|------|------|------|
| 图片→颜色区域→初始曲线 | **VTracer** (开源) | 不重写，`pip install vtracer` 直接调用 |
| SVG解析 | **svgpathtools** (开源) | 解析VTracer输出的path |
| SVG/DXF/IBL/JSON输出 | **svgpathtools/ezdxf** (开源) | 用开源库生成 |
| Shared Boundary 提取 | **自研** | 项目核心创新点 |
| 工程约束验证 | **自研** | 间距/半径/自交/断线 |
| Creo 工作流衔接 | **自研** | IBL格式适配 |

## Creo 工作流

1. 本工具导出 IBL 文件
2. Creo → Import / Get Data → Curve → 选择 IBL
3. 生成基准曲线
4. Composite Curve 合并连续曲线
5. Sweep → 圆形截面 Φ0.6mm → 掐丝金属丝实体

## 版本

- **V1.0**: 自研 K-Means + Bezier 引擎（已废弃，改为VTracer）
- **V2.0** (当前): VTracer 引擎 + Shared Boundary + 工程验证 + 多格式导出

## 第三方依赖与许可证（规格书第五十一章）

| 项目 | 许可证 | 用途 | 仓库 |
|------|--------|------|------|
| **VTracer** | MIT | 矢量化引擎（图片→颜色区域→Spline） | https://github.com/visioncortex/vtracer |
| **image-to-svg** | MIT | UI/流程参考项目 | https://github.com/edo1z/image-to-svg |
| **svgpathtools** | MIT | SVG Path 解析 | https://github.com/mathandy/svgpathtools |
| **ezdxf** | MIT | DXF 读写 | https://github.com/mozman/ezdxf |
| **OpenCV** | Apache-2.0 | 图像处理/区域mask | https://github.com/opencv/opencv |
| **NumPy** | BSD-3-Clause | 数值计算 | https://github.com/numpy/numpy |
| **scikit-learn** | BSD-3-Clause | K-Means（保留备用） | https://github.com/scikit-learn/scikit-learn |
| **FastAPI** | MIT | Web 框架 | https://github.com/tiangolo/fastapi |
| **Lumina-Layers** | GPL-3.0 | 仅作掐丝珐琅模式参考（不复制源码） | https://github.com/lumina-layer-studio/Lumina-Layers |

> **许可证说明**：
> - VTracer 采用 MIT 许可，可自由使用/修改/分发，无需开源衍生代码。
> - Lumina-Layers 为 GPL-3.0，本项目**仅参考其算法思路**，不复制其源码，避免 GPL 传染。
> - 若后续涉及 Potrace（GPL），需特别注意许可证义务；本项目优先 MIT 路线的 VTracer。
