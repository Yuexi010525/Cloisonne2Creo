# V2.2 Line Art Engineering 评审请求

**版本**: V2.2
**日期**: 2026-09-03
**评审人**: ChatGPT
**提交**: Yuexi010525/Cloisonne2Creo @ main

---

## 一、本次完成内容

按第五份规格书（开源掐丝模型生成器推荐-5.html）执行 V2.2 "Line Art Engineering" 改造：

### P0 后端（全部完成）
1. **Skan Graph Engine** — `backend/lineart/graph_skan.py`，基于 skan 0.13.1，默认引擎，legacy fallback
2. **验证语义重构** — `backend/lineart/validator.py`，hard_collision(＜线径→error) + dense_spacing_warning(线径~推荐间距→warning)，端点/junction 处连接不判定碰撞
3. **Stroke/Branch/Centerline 命名** — pipeline 输出新结构，兼容旧 boundaries/curves

### P1 UI（全部完成）
4. **生成模式选择** — 自动/彩色掐丝/黑白线稿/普通SVG/仅轮廓
5. **线稿参数面板** — 二值阈值/去噪/毛刺/保留细节/中心线算法/Graph引擎
6. **Debug 图层** — 原图/二值Mask/Skeleton/修剪后/最终曲线
7. **Validation Panel** — 线稿模式显示 Stroke/Branch/Junction/Endpoint/实体碰撞/过密警告

---

## 二、关键数据

### Skan vs Legacy A/B 对比（用户线稿，输出100mm）

| 指标 | Skan (默认) | Legacy |
|------|------------|--------|
| Branch数 | **200** | 578 |
| 平均边长(px) | **104.4** | 36.5 |
| Cycle数 | **15** | 11 |
| Curve减少 | **65.4%** | - |
| 运行时间 | 2.287s | 0.06s |

### 完整管线结果（用户线稿）
- V2.1 (Legacy): 551 curves / 460 merged
- V2.2 (Skan): **173 curves / 164 merged**（-68.6%）
- hard_collision: 23 / dense_warning: 17 / self_intersection: 0
- 彩色模式零回归 ✓

---

## 三、待决策问题

### Q1: hard_collision=23 是否可接受？
线稿模式下用户线稿有 23 对曲线中间部分距离 < 0.6mm（线径）。这些是线稿本身的密集区域（眼睛、脚趾、细节），不是算法错误。端点/junction 处的连接已排除。
- **选项A**: 接受，status=error 是正确的制造警告（用户可用更细线径或修改线稿）
- **选项B**: 增加"线稿模式忽略 hard_collision"开关，只显示 dense_warning
- **选项C**: 调整端点容差（当前 0.25mm），进一步排除近距离曲线

### Q2: Skan 运行时间 2.3s 是否可接受？
Skan 比 Legacy 慢 38 倍（2.3s vs 0.06s），但 Curve 质量更高。规格书未设性能上限。
- **选项A**: 接受，LineArt 不执行 O(n²) SharedBoundary，2.3s 可接受
- **选项B**: 增加"快速模式"用 Legacy，"高精度模式"用 Skan
- **选项C**: 优化 Skan 调用（如减少 path_coordinates 采样点）

### Q3: 自动检测误判风险
当前 LineArtDetector 基于颜色数/饱和度/背景比例判断。灰度图、低饱和彩色图可能误判为线稿。
- **选项A**: 保持当前基础版，P2 增强
- **选项B**: 增加"不确定时优先彩色"策略（V2.1 已实现）
- **选项C**: 增加用户确认步骤（自动检测后提示"检测为线稿，是否使用线稿模式？"）

### Q4: Medial Axis 是否在 V2.2 启用？
规格书将 Medial Axis A/B 列为 P2（以后做），当前仅 Skeletonize。代码保留 medial_axis 但 UI 隐藏。
- **选项A**: 按规格书 P2 推迟
- **选项B**: V2.2 就启用 Medial Axis 作为可选算法，做 A/B 对比

### Q5: 曲线合并后 hard_collision 变化
A/B 对比（未合并）hard_collision=1，但完整管线（合并后）hard_collision=23。合并后的曲线组可能与其他曲线靠近。
- **选项A**: 正常现象，合并后曲线更长，与其他曲线靠近概率增加
- **选项B**: 验证应在合并前执行（用 raw curves），合并后只做拓扑检查
- **选项C**: 合并时增加"避免与其他曲线过近"的约束

---

## 四、P2 以后做（规格书明确推迟）

- Medial Axis A/B 对比
- 自动识别增强
- 手工编辑骨架
- 真正的几何 Validator

---

## 五、验证方式

- [x] Skan 引擎单测通过（edges 578→200，-65%）
- [x] 用户线稿集成测试通过（173 curves / 164 merged）
- [x] 5 项线稿验收（粗直线/粗圆环/粗十字/用户线稿/自动检测）— V2.1 已过，V2.2 Skan 进一步优化
- [x] 彩色模式 Test01 零回归（regions=2, boundaries=1, status=ok）
- [x] API 线稿模式测试通过（mode=lineart, engine=lineart_skeleton）
- [x] API 自动检测测试通过（线稿图→lineart）
- [x] Skan vs Legacy A/B 对比表完成
- [x] 前端 UI 模式切换测试（参数面板动态显示/隐藏）

---

## 六、下一步建议

请 ChatGPT 评审：
1. 上述 5 个待决策问题的选择
2. V2.2 是否可以标记为完成并进入 V2.3
3. P2 功能的优先级排序
4. 是否需要补充其他测试或文档
