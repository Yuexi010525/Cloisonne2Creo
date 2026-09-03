# 问题分析：第二张图分析成功后，二值 Mask 残留上一张图数据

**日期**: 2026-09-03
**版本**: V2.2.1 (commit 2255ee0 基础上新增修复)
**状态**: 已修复，待 ChatGPT 审查

---

## 一、问题现象

用户连续分析两张图片：
1. 第一张图（线稿）分析成功 → 二值 Mask / Skeleton / 修剪后图层正常显示
2. 导入第二张图并分析成功 → 二值 Mask 图层里**还留有第一张图的数据**

即：切换图片后，线稿调试图层（binary/skeleton/pruned）没有随新结果更新或被清除，导致显示旧图残留。

---

## 二、根因分析

### 2.1 问题代码

`frontend/js/app.js` 的 `renderResult()` 函数有 3 个分支：

| 分支 | 触发条件 | 设置哪些图层 |
|------|---------|-------------|
| svg/outline 分支 | `result.mode === 'svg' \|\| 'outline'` | 只设 original，隐藏 regions/boundaries |
| lineart 分支 | `result.mode === 'lineart'` | 设置 binary/skeleton/pruned，隐藏 regions/boundaries |
| 彩色分支 | 其他（彩色掐丝） | **只设置 regions/boundaries，不碰 binary/skeleton/pruned** |

**问题**：彩色分支和 svg/outline 分支**完全没有清除**线稿调试图层（`img-binary`/`img-skeleton`/`img-pruned`）。

### 2.2 触发场景

1. 用户第一次分析**线稿图** → lineart 分支执行 → `img-binary` 的 `src` 设为第一张图的 binary mask，且因 `layer-binary` checkbox 勾选而显示
2. 用户导入**第二张图**（可能是彩色图，走彩色分支）→ 彩色分支只更新 regions/boundaries，`img-binary` 的 `src` **保持第一张图的数据**，`display` 也保持原状态
3. 用户切到线稿模式查看图层（或勾选 binary checkbox）→ 看到的是**第一张图的残留数据**

即使第二张图也走线稿分支，只要第二次 `preview_images` 中某个 key 缺失（如 `pruned_skeleton`），该图层也会残留旧图。

### 2.3 本质

这是**前端状态没有在每次渲染前重置**的问题。各分支只"设置自己的图层"，但从不"清除不属于自己的图层"，导致跨模式/跨图片切换时旧数据残留。

---

## 三、修复方案

### 3.1 修改内容

`frontend/js/app.js`：

1. **新增两个清理函数**：
   - `clearLineartLayers()` — 清除 binary/skeleton/pruned 图层的 `src` 和 `display`
   - `clearColorLayers()` — 清除 regions/boundaries 图层的 `src` 和 `display`

2. **三个分支统一清理**：
   - svg/outline 分支：调用 `clearColorLayers()` + `clearLineartLayers()`
   - lineart 分支：原 `layerImages.regions.style.display = 'none'` 改为 `clearColorLayers()`
   - 彩色分支：在设置 regions/boundaries 前调用 `clearLineartLayers()`

3. **关键改进**：清理时用 `removeAttribute('src')` 不仅隐藏，还移除 src，确保下次显示时不会回退到旧图。

### 3.2 修复后的代码逻辑

```javascript
// 清除线稿调试图层 (binary/skeleton/pruned) — 防止上一张图数据残留
function clearLineartLayers() {
  const keys = ['binary', 'skeleton', 'pruned'];
  keys.forEach(key => {
    const target = layerImages[key];
    if (!target) return;
    target.removeAttribute('src');
    target.style.display = 'none';
  });
}

// 清除彩色图层 (regions/boundaries)
function clearColorLayers() {
  const keys = ['regions', 'boundaries'];
  keys.forEach(key => {
    const target = layerImages[key];
    if (!target) return;
    target.removeAttribute('src');
    target.style.display = 'none';
  });
}
```

---

## 四、验证

- [x] `node --check frontend/js/app.js` 通过
- [x] 缓存版本号更新为 `v=20260903-02`（确保浏览器加载新代码）
- [ ] 需要浏览器实际测试：线稿图 → 彩色图 → 检查 binary 图层无残留

---

## 五、待 ChatGPT 审查

1. 修复方案是否完整？是否有其他图层（如 `svg-container`）也存在类似残留问题？
2. 是否应该在 `renderResult()` **开头**统一重置所有图层，而不是在每个分支分别清理？（更健壮但改动更大）
3. `loadSvg()` 是否也会残留？线稿/彩色模式都调用它，SVG 内容是否可能跨图残留？
4. 是否应该在上传新文件时（`handleFile`）就清空所有预览图层，而不是等分析完成？

---

## 六、相关文件

- `cloisonne-generator/frontend/js/app.js` — 前端逻辑（本次修复）
- `cloisonne-generator/frontend/index.html` — 缓存版本号更新
