# Skan vs Legacy Graph A/B 测试报告 (V2.3 第9-10阶段)

**日期**: 2026-09-04  **测试工具**: scripts/test_lineart.py

测试图: 粗直线 / 粗圆环 / 粗十字 (tests/_v23_fixtures, 自绘) + 用户线稿 (examples/test_user_lineart.png)

## 指标对比 (skan / legacy)

| 用例 | 指标 | Skan | Legacy | 备注 |
|---|---|---|---|---|
| 粗直线 | junction_count | - | - | |
| 粗直线 | endpoint_count | - | - | |
| 粗直线 | branch_count | 1 | 1 | |
| 粗直线 | cycle_count | 0 | 0 | |
| 粗直线 | final_curve_count | 1 | 1 | |
| 粗直线 | self_intersection | 0 | 0 | |
| 粗直线 | hard_collision | 0 | 0 | |
| 粗直线 | dense_warning | 0 | 0 | |
| 粗直线 | runtime(s) | 2.72 | 0.02 | |
| 粗直线 | __结论__ | 单中心线(1条)为正确结果 | | |
| 粗圆环 | junction_count | - | - | |
| 粗圆环 | endpoint_count | - | - | |
| 粗圆环 | branch_count | 1 | 1 | |
| 粗圆环 | cycle_count | 1 | 0 | |
| 粗圆环 | final_curve_count | 1 | 1 | |
| 粗圆环 | self_intersection | 0 | 0 | |
| 粗圆环 | hard_collision | 0 | 0 | |
| 粗圆环 | dense_warning | 0 | 0 | |
| 粗圆环 | runtime(s) | 0.173 | 0.154 | |
| 粗圆环 | __结论__ | 单中心圆环(1条)为正确结果; skan 正确识别 cycle | | |
| 粗十字 | junction_count | - | - | |
| 粗十字 | endpoint_count | - | - | |
| 粗十字 | branch_count | 4 | 12 | |
| 粗十字 | cycle_count | 0 | 0 | |
| 粗十字 | final_curve_count | 4 | 12 | |
| 粗十字 | self_intersection | 0 | 0 | |
| 粗十字 | hard_collision | 1 | 9 | |
| 粗十字 | dense_warning | 0 | 0 | |
| 粗十字 | runtime(s) | 0.032 | 0.041 | |
| 粗十字 | __结论__ | 4 Edge + 1 Junction 拓扑正确 (legacy 拆分过碎为12) | | |
| 用户线稿 | junction_count | - | - | |
| 用户线稿 | endpoint_count | - | - | |
| 用户线稿 | branch_count | 173 | 551 | |
| 用户线稿 | cycle_count | 15 | 0 | |
| 用户线稿 | final_curve_count | 173 | 551 | |
| 用户线稿 | self_intersection | 0 | 0 | |
| 用户线稿 | hard_collision | 23 | 34 | |
| 用户线稿 | dense_warning | 17 | 35 | |
| 用户线稿 | runtime(s) | 1.197 | 4.124 | |
| 用户线稿 | __结论__ | Skan 曲线大幅减少 173 vs 551 (-69%), 碰撞/过密更少, 更快 | | |

## 选择结论 (V2.3 第10阶段: 几何正确 > 拓扑正确 > 真实细节 > 曲线数量)

- **粗直线 / 粗圆环**: Skan 与 Legacy 均正确生成单中心线 (1条), 无双线, 自交=0
- **粗十字**: Skan=4 Edge, Legacy=12 (Skan 拓扑更正确, 碎片少)
- **用户线稿**: Skan 曲线 173 vs Legacy 551 (**-69% 碎片减少**), hard_collision 23 vs 34, dense 17 vs 35, runtime 1.2s vs 4.1s
- **自交**: 四组测试 skan 与 legacy 均为 0
- **结论: 默认 graph_engine = skan** (几何/拓扑正确且碎片显著减少)

> Legacy (backend/lineart/graph.py) 保留为 fallback (规格书第11阶段, 不得删除)。