# 给 ChatGPT：Cloisonne2Creo 本地服务"总是无法启动"问题分析

> 症状：浏览器访问 http://127.0.0.1:8765 报 ERR_CONNECTION_REFUSED；双击 start.bat"没反应"。
> 根因已定位并修复（commit c1d97eb），以下是完整分析，供你评审并给长期方案。

---

## 一、症状与排查过程

1. 用户双击 start.bat → 无窗口/闪退/报"系统找不到指定路径"、`No suitable Python runtime found`。
2. 浏览器访问 127.0.0.1:8765 → `ERR_CONNECTION_REFUSED`（服务进程不在、端口未监听）。
3. 后台用 `pythonw.exe` 启动的进程多次被静默回收（日志显示服务曾正常 health 200，随后进程消失）。

## 二、根因（已确认）

### 根因 1（主因，已修复）：start.bat 括号语法错误
```bat
if errorlevel 1 (
    echo Installing dependencies (first run may take a few minutes)...   ← 这个圆括号！
    ...
) else (
    ...
)
```
cmd 的 `if (...) else (...)` 块内出现 `(` 会被解析为嵌套子块边界，报中文错误 `此时不应有 ...。`，启动流程直接中断。
**修复**：去掉括号，改 `echo Installing dependencies, first run may take a few minutes...`（commit c1d97eb）。
修复后实测：双击/命令行运行 start.bat → 服务正常启动，浏览器自动打开，health 200。

### 根因 2（环境陷阱）：py launcher 与 PATH 默认版本不可靠
- `py --list` 默认版本是 **3.14**（`-V:3.14 *`），依赖装在 3.12。
- PATH 中 `python` 第一个解析到 Doubao 沙箱的 python（`...\sandbox_runtime\...\python.exe`），不是项目用的 3.12。
- start.bat 已用完整路径优先：`C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe`（已验证存在），规避了该陷阱。

### 根因 3（长期稳定问题）：后台进程生命周期无保障
- 用 `pythonw.exe`（无控制台）后台启动的 uvicorn 进程，多次运行一段时间后进程消失（无报错日志），导致再次 ERR_CONNECTION_REFUSED。
- 当前 start.bat 是前台运行（`%PYTHON_CMD% main.py`），窗口关闭即停——对"开机常驻"不友好。

## 三、请 ChatGPT 评审/给建议的问题

1. **后台常驻方案**：本地工具推荐哪种启动方式最稳？
   - A. 继续 start.bat 前台窗口（简单，但窗口关即停、用户可能误关）
   - B. `pythonw` + 写 PID 文件的守护脚本（我此前用但被静默回收）
   - C. Windows 任务计划程序（Task Scheduler）注册"登录时启动 + 崩溃重启"？
   - D. NSSM 之类注册为 Windows 服务？
   哪种对"普通工程师用户、不折腾"最友好且最不易再出现 ERR_CONNECTION_REFUSED？

2. **进程被静默回收的可能原因**：pythonw 无窗口进程在什么情况下会被 Windows 杀掉？（内存压力/无窗口会话/杀软？）是否需要显式 `SetConsoleCtrlHandler` 或保证工作目录/日志句柄？

3. start.bat 是否还有其他健壮性问题（中文路径 `F:\000-deepseek\掐丝模型生成器\` 下的 cmd 兼容性、`start "" url` 的默认浏览器等）？

## 四、当前状态

- 服务：start.bat 已能正常启动并保持（health 200，pid 34716）。
- GitHub：V2.3 已推送（97b5cec / bbb4c9e），本次 start.bat 修复 c1d97eb。
