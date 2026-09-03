# Cloisonne2Creo V2.1 线稿模式 — 评审请求

> 请 ChatGPT 评审当前实现，给出下一轮（V2.2 或 V2.1 优化）的改造指令。

## 仓库信息

- **GitHub**：https://github.com/Yuexi010525/Cloisonne2Creo
- **最新 Commit**：`d723ad8`（V2.1 线稿模式）
- **上一轮评审**：`ac6cc87`（线稿双线问题 ISSUE 文档）→ ChatGPT 给出 V2.1 线稿模式规格书（Stroke→Skeleton 中心线方案）

## 本轮完成内容（V2.1 线稿模式）

按照 ChatGPT 上一轮规格书，实现了**输入语义分叉**架构：

```
图片
  │
Input Classifier (自动检测)
  ├─ 彩色填充图 → Region → SharedBoundary（V2.0/V2.1 原有逻辑，完全不动）
  └─ 黑白线稿   → Stroke → Skeleton（中心线）← V2.1 新增
```

### 新增模块 `backend/lineart/`（6 文件）

| 文件 | 职责 | 复用开源 |
|------|------|----------|
| `detector.py` | 自动线稿检测（颜色数≤12 / 饱和度≤60 / 白底≥15% / 黑底≥2% / 灰度标准差≥40） | NumPy |
| `preprocess.py` | BW 二值化（Otsu + 中值去噪 + 形态学闭运算 + 边界1px清除） | OpenCV |
| `skeleton.py` | 骨架化（默认 skeletonize，可选 thin / medial_axis） | **scikit-image** |
| `graph.py` | 骨架→图（8 邻域：1=endpoint / 2=normal / ≥3=junction，Edge 有序点串） | NumPy |
| `pruning.py` | 毛刺修剪（迭代删除 <0.8mm 末端分支，`keep_fine_segments` 开关） | NumPy |
| `pipeline.py` | 线稿管线（坐标转换→简化→Bezier→G0/G1合并→验证→SVG/DXF/IBL） | 复用现有全部 Curve/Validator/Exporter |

### 关键规则（严格遵循规格书）

- Line Art 模式**禁止**使用 SharedBoundaryExtractor，直接 Black Mask → Skeleton
- 彩色图逻辑**完全不动**
- 骨架化**不自研**，调用 scikit-image
- 自动检测**不确定时优先彩色模式**（不错误进入 Line Art）
- 交叉处保留 Junction Node，不强行合并
- 不重写 Validator，不先优化 UI

## 验收测试结果（5 项全过）

| 测试 | skeleton edges | curves | merged | 自交 | 线距冲突 | 结果 |
|------|---------------|--------|--------|------|----------|------|
| 粗黑直线 | 1 | 1 | 1 | 0 | 0 | **单中心线** ✅ |
| 粗圆环 | 1 | 1 | 1(闭合) | 0 | 0 | **单中心圆线** ✅ |
| 粗十字 | 12 | 12 | 6 | 0 | 8 | 交叉拓扑正确 ✅ |
| 用户线稿(test_user_lineart.png) | 551 | 551 | 460 | **0** | 1553 | **无双线** ✅ |
| 自动检测 | — | — | — | — | — | 3/3 正确识别 ✅ |

### 用户线稿对比（核心问题修复）

| 指标 | V2.0 彩色模式（基线） | V2.1 线稿模式 |
|------|----------------------|---------------|
| 粗线语义 | **笔画边缘（双线）** | **笔画中心（单线）** |
| Boundary/Curve 数 | 222 | 551 |
| Curve Group 数 | 217 | 460 |
| 自交数 | 23 | **0** |
| 线距冲突数 | 319 | 1553 |

**叠加对比图确认**：问号、呆毛、头顶弧线、眼睛椭圆、身体轮廓、脚、尾巴、底部基线——全部是单条红色中心线沿笔画中间走，V2.0 的"左右两条边缘平行线"已彻底消失。

### 彩色模式回归测试

Test01-04 全部通过，与 V2.1 几何核心基线完全一致，**无回归**。

## 修复的关键 Bug

1. **异常斜穿直线（141mm）**：原图顶行/左列有 1px 深色边框（灰度 23-28），Otsu 二值化当成前景；skeletonize 后 L 型边框在角点被 8 邻域 walk_edge 错误连接成对角线。修复：二值化后清除图像边界 1px（`border_crop_px=1`，可配置）。
2. **中文路径 PNG 保存失败**：OpenCV `imwrite` 不支持中文路径，改用 `cv2.imencode` + `ndarray.tofile`。

## 已知问题 / 需要评审的方向

### 问题 1：线距冲突数偏高（1553）

线稿模式产生 551 条曲线，密集区域（眼睛、脚趾、细节）线距 <0.8mm。这是线稿本身的特点（线稿线条本来就密），非 bug。但当前复用彩色模式的默认最小线距 0.8mm，可能过于严格。

**待决策**：线稿模式是否应该使用更小的默认最小线距（如 0.3mm）？还是在骨架阶段合并过近的平行骨架线？

### 问题 2：曲线数量偏多（551）

骨架化产生较多细碎边（551 edges，合并后 460）。主要原因：
- 骨架在交叉区域产生多个 junction 和短边
- 简化容差（0.15mm）对骨架点串可能偏严

**待决策**：是否需要在 graph 阶段增加共线短边合并？还是增大线稿模式的默认简化容差？

### 问题 3：UI 未接入线稿模式

后端已支持 `gen_mode=auto/lineart/color`，但前端 UI 尚未增加：
- 生成模式选择（自动/彩色掐丝/线稿/普通SVG/仅轮廓）
- 线稿模式参数面板（毛刺阈值、保留细小线段、中心线算法选择）
- 调试图层显示（原图/Mask/Skeleton/最终曲线 开关）

**待决策**：下一轮是否优先做 UI 接入？还是继续优化后端算法？

### 问题 4：medial_axis 未启用

规格书建议 medial_axis 作为 V2.2 实验选项，当前默认 skeletonize。UI 可未来增加"中心线算法：Skeletonize / Medial Axis"选择。

**待决策**：是否需要在下一轮实现 medial_axis 并做 A/B 对比？

### 问题 5：彩色图自动检测误判风险

低饱和度彩色图（如淡彩、水彩）可能被误判为线稿。当前策略是"不确定时优先彩色模式"，降低了误判风险，但仍可能有边界 case。

**待决策**：是否需要增加更鲁棒的检测特征（如边缘密度、颜色空间分布）？

## 下一轮建议优先级（供 ChatGPT 参考）

1. **UI 接入线稿模式**（让用户能实际使用，当前只能通过 API 参数调用）
2. **线稿模式专用工程参数**（更小默认线距、简化容差调整）
3. **骨架共线边合并**（减少曲线数量）
4. **medial_axis 实验对比**
5. **自动检测鲁棒性增强**

## 关键文件索引

- 实施报告：`docs/V2.1_LINEART_MODE_REPORT.md`
- 双线问题根因：`docs/ISSUE_lineart_double_lines.md`
- 线稿模块：`cloisonne-generator/backend/lineart/`
- 主管线分发：`cloisonne-generator/backend/pipeline.py`（`_run_lineart` + auto detect）
- 验收测试：`cloisonne-generator/tests/test_lineart_v21.py`
- 叠加对比图：`cloisonne-generator/tests/lineart_v21_debug/t4_user_lineart/07_overlay_verify.png`（本地，未入库）
- 依赖：`cloisonne-generator/requirements.txt`（+scikit-image>=0.20.0）

---

**请评审以上实现，给出下一轮改造指令（规格书）。** 重点关注：已知问题的优先级排序、UI 接入时机、线稿模式参数调优方向。
