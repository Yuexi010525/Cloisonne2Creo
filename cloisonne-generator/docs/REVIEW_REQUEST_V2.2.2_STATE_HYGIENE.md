# V2.2.2 Frontend State Hygiene — 实施完成，请求评审

**日期**: 2026-09-04
**状态**: 已实现 + 浏览器实测通过，待 ChatGPT 评审

---

## 一、本次改动概述

按第六份规格书的 V2.2.2 Frontend State Hygiene 要求执行，把"分支互相清理"升级为"渲染入口统一清空、各分支只负责渲染自己"。

## 二、P0 项（已完成）

### 1. renderResult 统一 reset ✅
- 新增 `resetAllPreviewLayers()`：按元素类型处理所有 `.preview-layer`（img 清 src，div 用 replaceChildren），并重置结果面板/preview-info/placeholder
- `renderResult()` 改为：先 `resetAllPreviewLayers()`，再 `switch(result.mode)` 分发
- 拆分为独立渲染函数：`renderLineartResult()` / `renderColorResult()` / `renderSvgResult()` / `renderOutlineResult()`
- 未知模式抛错 `未知结果模式: xxx`（主动暴露问题）

### 2. loadSvg 强制替换旧 DOM ✅
- `svgContainer.replaceChildren()` 后再 `innerHTML = svgText`

### 3. handleFile 立即清旧结果 ✅
- 新增 `clearPreviewForNewFile()`：选择新图片时立即 `resetAllPreviewLayers()` + `currentResult = null` + 禁用导出按钮
- 状态显示"图片已加载，点击开始分析"，避免误以为旧结果属于新图

### 4. analysis requestId 防旧请求覆盖 ✅
- 新增全局 `analysisId`，每次点击分析 `++analysisId`
- fetch 返回后、render 前、catch/finally 中都校验 `requestId !== analysisId`，过期结果直接丢弃

## 三、额外发现并修复的后端问题

**严格 switch 暴露了一个后端缺陷**：默认彩色分支（`main.py` 的 CloisonnePipeline 摘要响应）**缺少 `"mode": "cloisonne"` 字段**。

- V2.2.1 靠 renderResult 的 else 兜底掩盖了它（mode undefined 时落到彩色分支）
- V2.2.2 严格 switch 后彩色分析直接抛 `未知结果模式: undefined`
- 已修复：在 `main.py` 默认彩色分支 summary 中补 `"mode": "cloisonne"`

建议：后续所有后端响应都应显式带 `mode` 字段，前端不再依赖"默认兜底"。

## 四、P1 项（已完成）

- 预览图层统一加 `data-preview-layer` 属性（common/color/lineart/svg）
- 缓存版本号更新为 `v=20260903-03`
- Console 调试日志保留（[renderResult] group）

## 五、浏览器实测结果（全部通过）

| 场景 | 结果 |
|------|------|
| 彩色模式分析 | ✅ 分析完成，img-regions 有 src，img-binary 无残留 |
| 线稿模式分析 | ✅ 分析完成，img-binary 有 src，img-regions 无残留 |
| 换新图片立即清空 | ✅ img-regions/src 均无、svg 空、状态"等待分析" |
| SVG 模式 | ✅ 分析完成 |
| Outline 模式 | ✅ 分析完成 |
| 自动检测模式 | ✅ 分析完成 |
| Console | ✅ 无任何 error/warning |

## 六、待 ChatGPT 审查

1. `resetAllPreviewLayers()` 用 `.preview-layer` class + `data-preview-layer` 属性的双标识，是否还需进一步演进到 PreviewState（V2.3）？
2. requestId 机制是否需要在 `loadSvg()` 的异步 fetch 中也应用（避免旧 SVG fetch 晚返回覆盖新结果）？
3. 后端 `mode` 字段目前四个分支都有了吗？（svg/outline/lineart/cloisonne 均已确认有）是否还有其它响应缺 mode？
4. `resetAllPreviewLayers()` 里 `previewPlaceholder.style.display = ''` 恢复默认 block，是否符合预期？
5. 是否应把 `renderColorInteraction()` 里的 color-list 也纳入重置范围（换图后旧 color chips 是否残留）？

## 七、相关文件

- `cloisonne-generator/frontend/js/app.js` — 前端重构（V2.2.2 核心）
- `cloisonne-generator/frontend/index.html` — data-preview-layer 属性 + 缓存版本号
- `cloisonne-generator/main.py` — 彩色分支补 mode 字段
