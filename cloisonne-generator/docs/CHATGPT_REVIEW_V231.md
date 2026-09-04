# V2.3.1 Windows 启动稳定方案 — 请 ChatGPT 评审

日期：2026-09-04
项目：Cloisonne2Creo（掐丝珐琅图片转 Creo 曲线生成器，Windows 本地服务，端口 8765）
仓库：github.com/Yuexi010525/Cloisonne2Creo（main）

## 背景

按你规格书《开源掐丝模型生成器推荐-9.html》末尾的 V2.3.1 Windows Runtime & Launcher 方案完成实施。
核心改动：放弃 pythonw+PID 守护，采用 **start.bat 前台救援 + Task Scheduler 登录自启双模式**；新增 .venv、日志、healthcheck/stop/restart/update 脚本族、launcher 安装器；/health 增强。

## 已完成并实测通过

| 项 | 实测结果 |
|---|---|
| /api/health 增强 | 返回 `{"status":"ok","service":"Cloisonne2Creo","version":"2.3.1","pid":27336,"port":8765}` |
| start.bat（.venv 优先→依赖检查→单实例→启动→健康轮询 15s→开浏览器→失败不闪退+日志） | 全流程通过，2s 内 Health OK |
| 单实例 | 连续双击第二次显示 "already running" 只开浏览器 |
| healthcheck.bat / stop.bat（PID+commandline 精准停）/ restart.bat | 全部实测通过（stop 校验 commandline 含 main.py 后 taskkill /pid） |
| logs/startup.log + server.log | UTF-8，记录 START/Python/Version/CWD/Port/依赖/health/error |
| .venv | Python 3.12 建好，依赖装齐，彩色分析+SVG/DXF/IBL/JSON 导出全部回归通过 |
| README Windows 快速开始（方式A start.bat / 方式B install_task.bat） | 已更新 |

## 需要你确认的 4 个点

**1. RestartOnFailure 间隔被 Windows 限制为最小 1 分钟**
规格书写 5 秒，但 Task Scheduler 的 RestartOnFailure `Interval` 最小支持 PT1M，写 PT5S 直接报 `0x80041318 (Interval:PT5S)`。
我改成了 **1 分钟 × 5 次**。能否接受？如果确实需要秒级自愈，需要另写守护逻辑（与"不用自制守护"原则冲突，所以我没做）。

**2. requirements.txt 版本修正**
原锁定 scipy==1.11.0 / scikit-learn==1.3.0 / shapely==2.0.0，在 Python 3.12 无 wheel，pip 源码编译失败。
已按系统实测可运行版本改为 scipy==1.18.1 / scikit-learn==1.9.0 / shapely==2.1.2（.venv 与系统 Python 均验证通过）。

**3. Task Scheduler 用 python.exe 还是 pythonw.exe**
用 python.exe（登录后弹一个黑色控制台窗口，但稳定、日志可见、无静默回收风险）；
pythonw.exe 无窗口但之前遇到过"静默回收"问题。当前用 python.exe 保稳定。可以吗？

**4. start.bat 服务窗口方案**
服务在最小化 cmd 窗口运行（关闭即停止），主窗口做检查+轮询+开浏览器后退出。符合预期吗？

## 已知限制（环境导致，非脚本 bug）

当前自动化会话为非提升令牌（Medium IL），无法完成 Task Scheduler 实际注册（Access denied）。
install_task.bat 已加**自动提权**（双击时弹 UAC），用户确认后即可注册。请确认提权方案正确。
