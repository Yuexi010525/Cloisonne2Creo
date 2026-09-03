# -*- coding: utf-8 -*-
"""V2.2.2 回归测试：彩色模式 + 多模式下载"""
import json, urllib.request, urllib.error, os

BASE = "http://127.0.0.1:8765"
IMG = r"F:\000-deepseek\掐丝模型生成器\cloisonne-generator\examples\test03_flower.png"

def analyze(mode):
    import uuid
    boundary = uuid.uuid4().hex.encode()
    body = b""
    with open(IMG, "rb") as f:
        img = f.read()
    body += b"--" + boundary + b"\r\n"
    body += b'Content-Disposition: form-data; name="file"; filename="test03_flower.png"\r\n'
    body += b"Content-Type: image/png\r\n\r\n" + img + b"\r\n"
    body += b"--" + boundary + b"\r\n"
    body += b'Content-Disposition: form-data; name="gen_mode"\r\n\r\n' + mode.encode() + b"\r\n"
    body += b"--" + boundary + b"--\r\n"
    req = urllib.request.Request(BASE + "/api/analyze", data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, json.loads(r.read())

for mode in ("cloisonne", "svg", "outline"):
    try:
        st, d = analyze(mode)
        svg_len = len(d.get("svg") or "")
        print(f"{mode}: HTTP={st} mode={d.get('mode')} svg={svg_len} dxf={bool(d.get('dxf_base64'))} ibl={bool(d.get('ibl_text'))}")
        # 测试下载接口
        for f in ("svg", "dxf", "ibl", "json"):
            try:
                r2 = urllib.request.urlopen(BASE + f"/api/download/{f}", timeout=30)
                print(f"  download/{f}: HTTP={r2.status} size={len(r2.read())}")
            except urllib.error.HTTPError as e:
                print(f"  download/{f}: HTTP={e.code} {e.read()[:120]}")
    except Exception as e:
        print(f"{mode}: ERROR {e}")
