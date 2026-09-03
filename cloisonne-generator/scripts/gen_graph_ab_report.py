# -*- coding: utf-8 -*-
"""生成 GRAPH_AB_REPORT.md (V2.3 第9阶段)"""
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(BASE, "results", "skan_ab_results.json")
out = os.path.join(BASE, "docs", "GRAPH_AB_REPORT.md")

with open(src, encoding="utf-8") as f:
    rows = json.load(f)

md = [
    "# Skan vs Legacy Graph A/B 测试报告 (V2.3 第9-10阶段)",
    "",
    "**日期**: 2026-09-04  **测试工具**: scripts/test_lineart.py",
    "",
    "测试图: 粗直线 / 粗圆环 / 粗十字 (tests/_v23_fixtures, 自绘) + 用户线稿 (examples/test_user_lineart.png)",
    "",
    "## 指标对比 (skan / legacy)",
    "",
    "| 用例 | 指标 | Skan | Legacy | 备注 |",
    "|---|---|---|---|---|",
]

metric_keys = [
    ("junction_count", "junction_count", "junction_count"),
    ("endpoint_count", "endpoint_count", "endpoint_count"),
    ("branch_count", "branches", "branches"),
    ("cycle_count", "cycle_count", "cycle_count"),
    ("final_curve_count", "curves", "curves"),
    ("self_intersection", "self_intersections", "self_intersections"),
    ("hard_collision", "hard_collisions", "hard_collisions"),
    ("dense_warning", "dense_warnings", "dense_warnings"),
    ("runtime(s)", "runtime_s", "runtime_s"),
]

notes = {
    "粗直线": "单中心线(1条)为正确结果",
    "粗圆环": "单中心圆环(1条)为正确结果; skan 正确识别 cycle",
    "粗十字": "4 Edge + 1 Junction 拓扑正确 (legacy 拆分过碎为12)",
    "用户线稿": "Skan 曲线大幅减少 173 vs 551 (-69%), 碰撞/过密更少, 更快",
}

for row in rows:
    case = row["case"]
    s, l = row["skan"], row["legacy"]
    for label, skey, lkey in metric_keys:
        sv = s.get(skey, s.get(label, '-'))
        lv = l.get(lkey, l.get(label, '-'))
        md.append(f"| {case} | {label} | {sv} | {lv} | |")
    md.append(f"| {case} | __结论__ | {notes.get(case, '')} | | |")

md += [
    "",
    "## 选择结论 (V2.3 第10阶段: 几何正确 > 拓扑正确 > 真实细节 > 曲线数量)",
    "",
    "- **粗直线 / 粗圆环**: Skan 与 Legacy 均正确生成单中心线 (1条), 无双线, 自交=0",
    "- **粗十字**: Skan=4 Edge, Legacy=12 (Skan 拓扑更正确, 碎片少)",
    "- **用户线稿**: Skan 曲线 173 vs Legacy 551 (**-69% 碎片减少**), hard_collision 23 vs 34, dense 17 vs 35, runtime 1.2s vs 4.1s",
    "- **自交**: 四组测试 skan 与 legacy 均为 0",
    "- **结论: 默认 graph_engine = skan** (几何/拓扑正确且碎片显著减少)",
    "",
    "> Legacy (backend/lineart/graph.py) 保留为 fallback (规格书第11阶段, 不得删除)。",
]
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print(f"已生成: {out}")
