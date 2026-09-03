# -*- coding: utf-8 -*-
"""测试4个下载接口 + 检查SVG分层"""
import re, base64, urllib.request, json

BASE = "http://127.0.0.1:8765"

for f in ("svg", "dxf", "ibl", "json"):
    url = f"{BASE}/api/download/{f}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            print(f"{f}: HTTP={r.status} size={len(data)}")
            if f == "svg":
                open("tmp_dl_svg.out", "wb").write(data)
            elif f == "dxf":
                open("tmp_dl_dxf.out", "wb").write(data)
            elif f == "ibl":
                open("tmp_dl_ibl.out", "wb").write(data)
            elif f == "json":
                open("tmp_dl_json.out", "wb").write(data)
    except urllib.error.HTTPError as e:
        print(f"{f}: HTTP={e.code} {e.read()[:200]}")

s = open("tmp_dl_svg.out", encoding="utf-8").read()
print("--- SVG layer check ---")
print("has cloisonne-wire:", '<g id="cloisonne-wire">' in s)
print("has debug-labels:", '<g id="debug-labels"' in s)
print("debug-labels hidden:", "display:none" in s)
print("text count:", s.count("<text"))
m = re.search(r'viewBox="([^"]+)"', s)
print("viewBox:", m.group(1) if m else None)
# 检查text标签是否在debug-labels组内
labels_g = re.search(r'<g id="debug-labels"[^>]*>(.*?)</g>', s, re.S)
print("labels inside debug-labels:", bool(labels_g), "count:", labels_g.group(1).count("<text") if labels_g else 0)

print("--- DXF header check ---")
d = open("tmp_dl_dxf.out", "rb").read()
print("DXF bytes:", len(d), "starts:", d[:40])
print("has AC1015(R2010):", b"AC1015" in d)

print("--- IBL start check ---")
i = open("tmp_dl_ibl.out", encoding="utf-8").read()
print("IBL chars:", len(i), "head:", repr(i[:80]))
