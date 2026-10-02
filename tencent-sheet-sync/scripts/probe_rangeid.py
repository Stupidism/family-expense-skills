# -*- coding: utf-8 -*-
"""探测腾讯文档官方"跳转单元格"链接格式：用 set_link 写入探测链接再读回"""
import json, subprocess

PY = "<python3>"
SKILL = "<user>/.workbuddy/plugins/cache/workbuddy-builtin/tencent-docs-plugin/5.5.4-wb.38151288.g1ca4889a.hde0fbd244c72/skills/tencent-docs"

def call(tool, args):
    r = subprocess.run([PY, "tencentdocs.py", "tdoc_call", "sheet-mcp", tool, json.dumps(args, ensure_ascii=False)],
                       capture_output=True, text=True, cwd=SKILL, timeout=60)
    return r.stdout

# 1) 写一个普通 http 链接看 get_cell_data 返回的 hyperlinks 结构（用边界内的 U1=col 20）
out = call("set_link", {"file_id": "YOUR_FILE_ID", "sheet_id": "SHEET_6TgC25", "row": 0, "col": 21,
                        "url": "https://example.com/probe", "display_text": "probe1"})
print("set_link:", out[:300])

out2 = call("get_cell_data", {"file_id": "YOUR_FILE_ID", "sheet_id": "SHEET_6TgC25", "start_row": 0, "end_row": 0, "start_col": 21, "end_col": 21})
print("readback:", out2[:800])
