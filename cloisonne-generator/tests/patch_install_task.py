# -*- coding: utf-8 -*-
# Fix install_task.bat:
#  1) PROJECT_ROOT backslash before .venv (PYTHON_EXE detection)
#  2) RestartInterval PT5S -> PT1M (Windows Task Scheduler min is 1 minute)
p = r'F:\000-deepseek\掐丝模型生成器\cloisonne-generator\launcher\install_task.bat'
d = open(p, 'rb').read().decode('utf-8')

# 1) backslash before .venv
old1 = 'if exist "%PROJECT_ROOT%.venv\\Scripts\\python.exe" ('
new1 = 'if exist "%PROJECT_ROOT%\\.venv\\Scripts\\python.exe" ('
assert old1 in d, 'venv check not found'
d = d.replace(old1, new1)
print('venv check patched (added backslash)')

# 2) RestartInterval 5s -> 1min
old2 = '(New-TimeSpan -Seconds 5)'
new2 = '(New-TimeSpan -Minutes 1)'
assert old2 in d, 'restart interval not found'
d = d.replace(old2, new2)
print('restart interval patched to 1min')

# 3) echo text update
old3 = 'echo   Restart : 5s x 5 on failure'
new3 = 'echo   Restart : 1min x 5 on failure (Windows min interval)'
if old3 in d:
    d = d.replace(old3, new3)
    print('echo text patched')

open(p, 'wb').write(d.encode('utf-8').replace(b'\n', b'\r\n'))
print('done')
