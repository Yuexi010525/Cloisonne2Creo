# 问题排查：线稿模式导出/预览异常（SVG 标签堆叠 + DXF/IBL 下载失败）

**日期**: 2026-09-04
**版本**: V2.2.2 (commit a5f46ea)
**状态**: 已定位根因，待 ChatGPT 确认修复方案

---

## 一、问题现象（用户报告）

线稿模式下，导出和预览出现多个问题：

1. **最终曲线图层显示异常**：E0000~E0508 等边界 ID 标签全部堆叠在预览区左上角，金色曲线不可见
2. **DXF 下载失败**：浏览器下载记录显示"网站出问题了"
3. **IBL 下载失败**：浏览器下载记录显示"网站出问题了"
4. SVG / JSON 下载正常（HTTP 200）

## 二、根因 1：最终曲线图层（前端 SVG 预览）标签堆叠

### 2.1 现象证据

浏览器实测（线稿模式分析完成后）：

```
previewStack  rect = [340, 223, 469, 469]   ← 正常（被原图撑开）
svgContainer  rect = [340, 223,   0,   0]   ← 塌缩为 0×0！
imgOriginal   rect = [340, 223, 469, 469]   ← 正常
```

svg-container 里的 `<svg>` 元素 `getBoundingClientRect()` 返回 **width=0, height=0**。

### 2.2 根因链

`frontend/js/app.js` 的 `loadSvg()`：

```javascript
svgContainer.replaceChildren();
svgContainer.innerHTML = svgText;
const svg = svgContainer.querySelector('svg');
if (svg) {
  svg.style.position = 'absolute';
  svg.style.top = '0';
  svg.style.left = '0';
  svg.style.width = '100%';
  svg.style.height = '100%';
}
```

配合 CSS（`frontend/css/style.css`）：

```css
.preview-layer { position: absolute; max-width: 100%; max-height: calc(100vh - 180px); }
.svg-layer svg { width: 100%; height: 100%; }
```

塌缩链：

1. `svg-container` 是 `.preview-layer` → `position: absolute`，且无显式 `width/height`（只有 max-*）
2. 内部 `<svg>` 被 JS 设为 `position: absolute` → **脱离 svg-container 的文档流**
3. svg-container 失去内容撑开 → **宽高塌缩为 0×0**（absolute 元素 auto 尺寸 = shrink-to-fit，内容为空）
4. svg 的 `width: 100% / height: 100%` 相对 0×0 父容器 → **也是 0×0**
5. SVG `viewBox="0 0 100.0 100.0"` 的全部内容被压缩进 0×0 元素 → 曲线不可见、文本标签全部重叠在左上角

### 2.3 已排除的干扰项

- **下载的 SVG 文件本身坐标正确**：后端生成的 SVG 中，`<text>` 标签 x 范围 13.0~97.2、y 范围 15.1~86.1，viewBox 0 0 100 100，173 个标签位置分布正常
- 问题仅发生在前端预览容器（svg-container）的尺寸塌缩

### 2.4 修复方向（待确认）

- 方案 A：CSS 给 `.svg-layer` 加 `width: 100%; height: 100%`，让 svg-container 填满 preview-stack（preview-stack 由原图撑开，尺寸正常）
- 方案 B：loadSvg 里不把 svg 设为 absolute，让它在 svg-container 内正常布局
- 方案 C：前端不依赖 svg-container 尺寸，改为给 SVG 直接设置 viewBox 缩放

## 三、根因 2：DXF 下载失败（HTTP 500）

### 3.1 现象证据

curl 实测（线稿模式分析后）：

```
GET /api/download/dxf
HTTP=500
{"detail":"DXF导出失败: 'LineArtPipeline' object has no attribute 'get_dxf_bytes'"}
```

浏览器下载记录显示"网站出问题了"。

### 3.2 根因

`main.py` 的 `/api/download/dxf`：

```python
@app.get("/api/download/dxf")
async def download_dxf():
    if current_result is None: ...
    try:
        dxf_bytes = current_pipeline.get_dxf_bytes()   # ← 直接调用
        ...
```

**`LineArtPipeline` 没有 `get_dxf_bytes()` 方法**（它只在 `run()` 里生成 `dxf_base64` 存进 result dict，见 `backend/lineart/pipeline.py` 224-232 行）。

- 彩色模式：`current_pipeline` 是 `CloisonnePipeline`，有该方法 → 正常
- 线稿模式：`current_pipeline` 是 `LineArtPipeline`，无该方法 → `AttributeError` → 500

### 3.3 修复方向（待确认）

- 方案 A：给 `LineArtPipeline` 增加 `get_dxf_bytes()` / `get_ibl_bytes()` 方法（把 run() 里生成的 dxf_base64/ibl_text 缓存为属性并返回）
- 方案 B：`main.py` 下载接口做兼容：`hasattr(current_pipeline, 'get_dxf_bytes')` 检查，否则从 `current_result["dxf_base64"]` 解码返回

## 四、根因 3：IBL 下载失败（HTTP 500）

### 4.1 现象证据

```
GET /api/download/ibl
HTTP=500
{"detail":"IBL导出失败: 'LineArtPipeline' object has no attribute 'get_ibl_bytes'"}
```

### 4.2 根因

与 DXF 完全同构：`main.py` `/api/download/ibl` 调用 `current_pipeline.get_ibl_bytes()`，**LineArtPipeline 没有该方法**。

## 五、附带发现（供参考）

1. **SVG 文件内含边界 ID 文本标签**：导出的 SVG 里每个曲线都带 `<text class="boundary-id">E0001</text>`（本测试图 173 个）。工程 CAD/SVG 使用场景通常不需要这些 ID 文本，建议做成可关闭的 Debug 层。
2. **JSON 下载正常**（HTTP 200，196KB），数据完整。
3. **DXF/IBL 数据本身可导出**：DXFExporter 接受 `{id, segments, closed}` 结构，lineart 的 curve_list 兼容；问题只在于 pipeline 没有暴露导出方法。

## 六、测试清单（供 ChatGPT 确认修复后验收）

- [ ] 线稿模式下"最终曲线"图层正常显示金色曲线，标签不再堆叠
- [ ] 线稿模式下 DXF 下载成功（HTTP 200，文件可打开，坐标正确）
- [ ] 线稿模式下 IBL 下载成功
- [ ] 彩色模式下载回归正常（不破坏现有功能）
- [ ] SVG 下载文件在浏览器/CAD 中打开坐标正确

## 七、相关文件

- `cloisonne-generator/frontend/js/app.js` — loadSvg()（svg absolute 定位问题）
- `cloisonne-generator/frontend/css/style.css` — .svg-layer / .preview-layer
- `cloisonne-generator/main.py` — /api/download/dxf、/api/download/ibl
- `cloisonne-generator/backend/lineart/pipeline.py` — LineArtPipeline（缺 get_dxf_bytes/get_ibl_bytes）
