# V2.2.2 完成报告：SVG 预览 + DXF/IBL 导出统一修复

**日期**: 2026-09-04
**依据**: 规格书《开源掐丝模型生成器推荐-8.html》中 ChatGPT 的 V2.2.2 修复指令
**状态**: 已实施并双向实测通过

---

## 一、本版本目标（来自 ChatGPT 修复指令）

修复：
1. SVG 最终曲线预览塌缩
2. LineArt DXF 下载失败
3. LineArt IBL 下载失败
4. SVG Debug 标签默认显示
5. 不同模式之间导出接口不统一

## 二、实施内容

### 1. SVG 预览修复（P0）

**问题**：svg-container 塌缩为 0×0，最终曲线标签全部堆叠左上角。

**修复**（按 ChatGPT 方案 B 为主）：
- `frontend/js/app.js` `loadSvg()`：删除 `svg.style.position = 'absolute'`，改为纯函数 `loadSvg(svgText='')`，内部 `replaceChildren()` 强制清空 → `innerHTML` 写入 → svg 设 `position:relative; display:block; width/height:100%; maxWidth:100%`，并 `removeAttribute('width'/'height')`
- `frontend/css/style.css`：给 `#svg-container` 明确尺寸 `position:absolute; inset:0; width:100%; height:100%`
- 原则：**父容器负责定位和尺寸，SVG 负责填充**

### 2. loadSvg 改为纯函数（P1）

- 不再自己 fetch `/api/svg`
- 各分支统一 `loadSvg(result.svg)`：renderColorResult / renderLineartResult / renderSvgLikeResult
- 消除"服务器 current_result 变化导致前后端状态错位"隐患

### 3. SVG 旧内容彻底清理（P1）

- `loadSvg()` 首行 `svgContainer.replaceChildren()`，禁止 append/insertAdjacentHTML 叠加

### 4. SVG Debug 标签默认关闭（P1）

- `exporters/svg_exporter.py`：SVG 分成两层
  - `<g id="cloisonne-wire">`：金色最终曲线（visible）
  - `<g id="debug-labels" style="display:none;">`：边界 ID 文本标签（默认隐藏）
- 前端新增 `[ ] 曲线编号` checkbox（默认关闭），控制 `#debug-labels` 组显示
- 实测：默认 173 个标签隐藏，勾选后显示

### 5. DXF 下载统一改为 current_result（P0）

`main.py` `/api/download/dxf`：
- 禁止 `current_pipeline.get_dxf_bytes()`（不同 Pipeline 不保证存在该方法）
- 改为 `current_result.get("dxf_base64")` → base64 decode → Response
- 无数据时 404 "当前结果没有DXF数据"

### 6. 删除无用 import（P0）

- 删除 `/api/download/dxf` 里的 `from backend.pipeline import CloisonnePipeline`（无实际作用）
- 下载接口不再依赖 Pipeline 类型

### 7. IBL 下载统一改为 current_result（P0）

- `main.py` `/api/download/ibl`：`current_result.get("ibl_text")` → Response
- 无数据时 404 "当前结果没有IBL数据"

### 8. SVG 下载统一读取 current_result（P1）

- `/api/download/svg` 和 `/api/svg`：从 `current_result.get("svg")` 读取

### 9. current_result 补 svg 字段（关键配套）

**发现**：CloisonnePipeline / LineArtPipeline 的 `run()` 返回结果都含 `"svg"` 字段，但 main.py 的彩色/线稿 summary 没有把 svg 放进 current_result → 下载接口会 404。已在三个分支（auto彩色 / lineart / 默认彩色）补 `"svg": result.get("svg")`。

### 10. 隐藏问题修复：svg/outline 模式未更新 current_result

**发现**：svg/outline 分支直接 return，未设置 `current_result` → 下载接口返回**上一张图/上一模式**的数据（数据串台）。

**修复**：svg/outline 分支也写入 current_result（含 mode/svg/image_info）。实测：
- svg 模式分析后 download/svg 返回**当前** svg
- svg 模式分析后 download/dxf/ibl 返回 **404"当前结果没有DXF数据"**（不再拿旧数据）

## 三、验收测试（双向实测）

### 后端（curl / Python）
| 模式 | /api/analyze | download/svg | download/dxf | download/ibl | download/json |
|---|---|---|---|---|---|
| lineart (test_user_lineart.png) | 200, svg=71134 | 200 (71134) | 200 (350KB) | 200 (210KB) | 200 |
| cloisonne (flower) | 200, svg=16507 | 200 (16507) | 200 (128KB) | 200 (75KB) | 200 |
| svg | 200, svg=18070 | 200 (18070) | 404 无DXF | 404 无IBL | 200 |
| outline | 200, svg=30319 | 200 (30319) | 404 无DXF | 404 无IBL | 200 |

### SVG 分层验证
- `#cloisonne-wire` 存在，含 173 条金色 path
- `#debug-labels` 存在，`display:none` 默认隐藏，173 个 text 标签全部在其内
- viewBox 0 0 100 100 正确

### DXF 完整性
- 350KB，ezdxf 可读回：164 条 SPLINE，版本 AC1024 (R2010)

### 前端浏览器实测
- svg-container 300×300（修复前 0×0），金色曲线正常显示
- 曲线编号默认隐藏，勾选后显示
- 下载 DXF / IBL 按钮点击后浏览器下载 completed（DXF 350KB / IBL 210KB）

## 四、相关文件

- `frontend/js/app.js` — loadSvg 纯函数化、renderSvgLikeResult 重构、曲线编号开关
- `frontend/css/style.css` — #svg-container 尺寸修复
- `frontend/index.html` — 新增"曲线编号"checkbox、版本号 v=20260904-01
- `exporters/svg_exporter.py` — SVG 分层（cloisonne-wire / debug-labels）
- `main.py` — 下载接口统一读 current_result、svg/outline 更新 current_result、补 svg 字段
- `tests/verify_v222.py`、`tests/regress_v222.py` — 验收脚本
