# -*- coding: utf-8 -*-
# Add admin auto-elevation to install_task.bat and uninstall_task.bat
# (Task Scheduler registration needs elevation on this machine)
for name in ['install_task.bat', 'uninstall_task.bat']:
    p = r'F:\000-deepseek\掐丝模型生成器\cloisonne-generator\launcher' + '\\' + name
    d = open(p, 'rb').read().decode('utf-8')

    elev = ('rem ---------- 自动提权: Task Scheduler 注册需要管理员权限 ----------\n'
            'net session >nul 2>&1\n'
            'if errorlevel 1 (\n'
            '    echo Requesting administrator privileges...\n'
            '    powershell -NoProfile -Command "Start-Process -FilePath \'%~f0\' -Verb RunAs"\n'
            '    exit /b 0\n'
            ')\n\n')

    anchor = 'title '
    idx = d.index(anchor)
    # insert after the first rem header block (after title line)
    line_end = d.find('\r\n', idx)
    insert_at = line_end + 2
    d = d[:insert_at] + '\r\n' + elev + d[insert_at:]
    open(p, 'wb').write(d.encode('utf-8').replace(b'\n', b'\r\n'))
    print('elevation added to', name)
print('done')
