# -*- coding: utf-8 -*-
"""从工具结果文件解码附件并保存 PDF（自动处理 PUSHDATA 包装）"""
import base64, json, sys

def decode(txt_path, out_pdf):
    with open(txt_path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    content = obj["data"]["content"] if "data" in obj else obj["content"]
    raw = base64.b64decode(content)
    if raw[:5] != b"%PDF-":
        # HSBC PUSHDATA 包装：首行为 %%PUSHDATA:...#END#%%，其后为 PDF 二进制
        head, _, rest = raw.partition(b"\n")
        if b"PUSHDATA" in head and rest[:5] == b"%PDF-":
            raw = rest
    assert raw[:5] == b"%PDF-", f"unexpected format: {raw[:60]!r}"
    with open(out_pdf, "wb") as f:
        f.write(raw)
    print(f"OK {out_pdf} {len(raw)} bytes")

if __name__ == "__main__":
    decode(sys.argv[1], sys.argv[2])
