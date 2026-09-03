# Cloisonne2Creo 基准测试报告 (V2.3)

**日期**: 2026-09-04  **版本**: V2.3  **commit**: (V2.3 整合后)

| 用例 | 图片尺寸(px) | 模式 | runtime(s) | regions | boundaries | branches | curves | 自交 | hard_collision | dense_warning | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Test01 两色 | 300x200 | cloisonne | 0.433 | 2 | 1 | 0 | 1 | 0 | 0 | 0 | ok |
| Test02 三色 | 240x240 | cloisonne | 0.129 | 4 | 5 | 0 | 5 | 0 | 0 | 0 | warning |
| Test03 花 | 400x400 | cloisonne | 1.467 | 14 | 20 | 0 | 20 | 0 | 0 | 0 | warning |
| Test04 猫 | 360x360 | cloisonne | 3.418 | 15 | 21 | 0 | 21 | 0 | 0 | 0 | warning |
| 粗直线 | 400x400 | lineart | 2.342 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | ok |
| 粗圆环 | 400x400 | lineart | 0.169 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | ok |
| 粗十字 | 400x400 | lineart | 0.026 | 0 | 0 | 4 | 4 | 0 | 1 | 0 | error |
| 用户线稿 | 1107x1107 | lineart | 1.262 | 0 | 0 | 173 | 173 | 0 | 23 | 17 | error |

> 说明: 全部数据来自真实运行 (scripts/benchmark.py), 非人工数据。