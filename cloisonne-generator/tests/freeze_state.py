# -*- coding: utf-8 -*-
"""状态冻结：检查依赖版本"""
import importlib.metadata as m
from pathlib import Path

pkgs = ['vtracer', 'scikit-image', 'skan', 'svgpathtools', 'ezdxf',
        'opencv-python', 'numpy', 'fastapi', 'uvicorn', 'pytest', 'Pillow', 'pydantic']
for p in pkgs:
    try:
        print(f"{p}: {m.version(p)}")
    except Exception:
        print(f"{p}: MISSING")

print("--- backend structure ---")
base = Path(r'F:\000-deepseek\掐丝模型生成器\cloisonne-generator')
for d in sorted([p for p in base.iterdir() if p.is_dir()]):
    print(d.name)
print("--- lineart ---")
la = base / 'backend' / 'lineart'
if la.exists():
    for p in sorted(la.iterdir()):
        print('  ', p.name)
print("--- tests ---")
t = base / 'tests'
if t.exists():
    for p in sorted(t.iterdir()):
        print('  ', p.name)
print("--- frontend js ---")
fj = base / 'frontend' / 'js'
if fj.exists():
    for p in sorted(fj.iterdir()):
        print('  ', p.name)
