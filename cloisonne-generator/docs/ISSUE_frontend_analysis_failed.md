# 问题排查请求：前端"分析失败"但后端 API 正常

**日期**: 2026-09-03
**版本**: V2.2 Line Art Engineering (commit 0d04a72)
**状态**: 待 ChatGPT 分析

---

## 一、问题现象

用户在浏览器中打开 http://127.0.0.1:8765，上传图片后点击"开始分析"，前端显示：

> 分析失败: [错误信息]

预览区显示"错误: [错误信息]"。

---

## 二、已排查事实

### 2.1 后端 API 正常

用 curl 直接测试后端 API，两种模式都返回 HTTP 200：

**线稿模式**:
```bash
curl -X POST http://127.0.0.1:8765/api/analyze \
  -F "file=@examples/test_user_lineart.png" \
  -F "gen_mode=lineart" \
  -F "output_width_mm=100"
# 返回: HTTP 200, mode=lineart, engine=lineart_skeleton, curves=173
```

**彩色模式**:
```bash
curl -X POST http://127.0.0.1:8765/api/analyze \
  -F "file=@examples/test01_two_colors.png" \
  -F "gen_mode=auto" \
  -F "output_width_mm=100"
# 返回: HTTP 200, mode=cloisonne, engine=vtracer, regions=2
```

**后端日志**:
```
INFO: 127.0.0.1:xxxxx - "POST /api/analyze HTTP/1.1" 200 OK
```

### 2.2 前端 JS 语法检查通过

```bash
node --check frontend/js/app.js
# exit code 0, 无语法错误
```

### 2.3 已修复的问题

1. **`/api/svg` 线稿模式 404** — `main.py` 中 `get_svg()` 检查 `current_pipeline.svg`，但 `LineArtPipeline` 用的是 `svg_content` 属性。已修复，增加 `svg_content` 检查。
2. **start.bat 编码乱码** — UTF-8 编码的中文 BAT 在 GBK 代码页下乱码，导致 `cd /d "%~dp0"` 失败、`echo` 被当成命令执行。已全英文重写。
3. **服务反复挂掉** — 用 `Start-Process python.exe` 和后台任务方式启动，进程会被系统静默回收。已改用 `pythonw.exe` 无窗口后台进程。

### 2.4 服务当前状态

- 启动方式: `pythonw.exe main.py`（无窗口后台进程）
- 端口: 127.0.0.1:8765
- 首页测试: HTTP 200
- API 测试: HTTP 200

---

## 三、V2.2 前端修改清单

`frontend/js/app.js` 在 V2.2 中做了以下修改：

1. **新增 DOM 引用**: `colorParams`, `lineartParams`, `colorResultGrid`, `lineartResultGrid`, `autoDetectResult`
2. **新增图层**: `binary`, `skeleton`, `pruned`（layerToggles 和 layerImages）
3. **新增函数**: `getCurrentMode()`, `updateModeUI()`
4. **模式切换事件**: `document.querySelectorAll('input[name="generate-mode"]').forEach(...)`
5. **formData 参数变更**:
   - `generate_mode` → `gen_mode`
   - `min_wire_spacing_mm` → `recommended_spacing_mm`
   - 新增: `binary_threshold`, `denoise_ksize`, `min_spur_length_mm`, `keep_fine_segments`, `skeleton_method`, `graph_engine`
6. **renderResult() 新增线稿模式分支**: 在 svg/outline 分支之后、彩色模式分支之前，增加了 `if (result.mode === 'lineart' || result.engine === 'lineart_skeleton')` 分支
7. **初始化调用**: 文件末尾增加 `updateModeUI()`

`frontend/index.html` 修改：
1. 版本号 V2.0 → V2.2
2. 生成模式增加: 自动检测、黑白线稿
3. 新增线稿参数面板（`id="lineart-params"`，默认隐藏）
4. 颜色处理面板增加 `id="color-params"`
5. Debug 图层增加: 二值Mask、Skeleton、修剪后
6. Validation Panel 分为彩色网格（`id="color-result-grid"`）和线稿网格（`id="lineart-result-grid"`）

---

## 四、可能的原因（待验证）

### 4.1 浏览器缓存旧版 app.js【可能性高】

用户之前访问过 V2.1 或更早版本，浏览器缓存了旧的 `app.js`。旧版 app.js：
- 用 `generate_mode` 参数名（后端兼容，不会报错）
- 不认识线稿模式的响应格式（`lineart_stats`, `strokes`, `centerlines` 等字段）
- `renderResult()` 可能因为访问不存在的字段而报错

**验证方法**: 用户按 Ctrl+F5 强制刷新后重试。

### 4.2 renderResult() 线稿分支运行时错误【可能性中】

线稿分支中有几处可能的运行时错误：

```javascript
// 运算符优先级问题: || 比 ?: 高
document.getElementById('res-la-strokes').textContent =
    ls.raw_branch_count || result.strokes ? result.strokes.length : '-';
// 实际解析为: (ls.raw_branch_count || result.strokes) ? result.strokes.length : '-'
// 如果 result.strokes 是 undefined, 不会报错(返回 '-'), 但如果是 null 可能有问题
```

```javascript
// result.validation 可能不存在?
const v = result.validation;
// 后续访问 v.hard_collision_count, 如果 v 是 undefined 会报错
```

```javascript
// loadSvg() 调用 /api/svg, 如果返回 404 不会抛异常, 但 SVG 不显示
loadSvg();
```

**验证方法**: 浏览器 F12 → Console 标签，查看红色错误信息。

### 4.3 前端请求参数与后端不匹配【可能性低】

前端发送 `gen_mode="auto"`，后端 `gen_mode: str = Form("")`，如果为空会回退到 `generate_mode="cloisonne"`。这应该不会导致失败。

前端发送 `recommended_spacing_mm`，后端有这个参数。兼容。

### 4.4 用户上传的图片有特殊问题【可能性低】

用户上传的图片可能是 webp、bmp 或其他格式，后端 `cv2.imdecode` 可能失败。但后端会返回 400 错误，前端会显示具体错误信息。

---

## 五、需要 ChatGPT 帮助分析的方向

1. **审查 `frontend/js/app.js` 的 renderResult() 函数**，特别是线稿模式分支，找出可能的运行时错误
2. **审查 `frontend/index.html`**，确认所有元素 ID 与 app.js 中的引用一致
3. **审查 `main.py` 的 `/api/analyze` 接口**，确认返回的 JSON 结构与前端 renderResult() 期望的一致
4. **建议增加前端错误处理**，比如在 renderResult() 外层加 try-catch，显示更详细的错误信息（包括堆栈）
5. **建议增加前端调试模式**，比如在 URL 加 `?debug=1` 时在页面上显示完整的 API 响应和渲染日志

---

## 六、相关文件

- `cloisonne-generator/frontend/js/app.js` — 前端逻辑（V2.2 修改）
- `cloisonne-generator/frontend/index.html` — 前端页面（V2.2 修改）
- `cloisonne-generator/main.py` — FastAPI 后端（V2.2 修改）
- `cloisonne-generator/backend/lineart/pipeline.py` — 线稿管线
- `cloisonne-generator/backend/lineart/validator.py` — 线稿验证器
- `cloisonne-generator/backend/lineart/graph_skan.py` — Skan 图引擎
- `cloisonne-generator/docs/V2.2_LINEART_ENGINEERING_REPORT.md` — V2.2 实施报告
