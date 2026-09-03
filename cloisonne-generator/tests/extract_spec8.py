# -*- coding: utf-8 -*-
"""提取规格书 html 文本"""
import re, html
from pathlib import Path

src = Path(r'F:\000-deepseek\掐丝模型生成器\开源掐丝模型生成器推荐-8.html')
raw = src.read_text(encoding='utf-8', errors='ignore')

raw = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.S|re.I)
raw = re.sub(r'<style[^>]*>.*?</style>', '', raw, flags=re.S|re.I)
raw = re.sub(r'<(p|div|li|h[1-6]|tr|br|section|article|blockquote|pre|code)[^>]*>', '\n', raw, flags=re.I)
raw = re.sub(r'</(p|div|li|h[1-6]|tr|td|th|section|article|blockquote|pre|code)>', '\n', raw, flags=re.I)
text = re.sub(r'<[^>]+>', '', raw)
text = html.unescape(text)

lines = [ln.strip() for ln in text.splitlines()]
out = []
blank = 0
for ln in lines:
    if ln.strip():
        out.append(ln.strip())
        blank = 0
    else:
        blank += 1
        if blank == 1:
            out.append('')

result = '\n'.join(out)
out_path = Path(r'F:\000-deepseek\掐丝模型生成器\spec8_all.txt')
out_path.write_text(result, encoding='utf-8')
print('字符数:', len(result))
print('行数:', len(out))
