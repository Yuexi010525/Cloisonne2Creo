# -*- coding: utf-8 -*-
# Patch start.bat log lines to ASCII-only (avoid GBK mojibake in startup.log)
p = r'F:\000-deepseek\掐丝模型生成器\cloisonne-generator\start.bat'
d = open(p, 'rb').read().decode('utf-8')

repl = [
    ('echo [%TS%] BAT_START Python=%PYTHON_CMD% >> "%STARTUP_LOG%"',
     'echo [%TS%] BAT_START Python selected >> "%STARTUP_LOG%"'),
    ('echo [%TS%] BAT_ERROR Python launcher failed: %PYTHON_CMD% >> "%STARTUP_LOG%"',
     'echo [%TS%] BAT_ERROR Python launcher failed >> "%STARTUP_LOG%"'),
]
for old, new in repl:
    if old in d:
        d = d.replace(old, new)
        print('patched:', old[:50])
    else:
        print('NOT FOUND:', old[:60])

open(p, 'wb').write(d.encode('utf-8').replace(b'\n', b'\r\n'))
print('done')
