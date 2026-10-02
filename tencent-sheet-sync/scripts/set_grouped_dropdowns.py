# -*- coding: utf-8 -*-
"""子类下拉重建：'主类｜子类' 分组格式+同主类同底色（API不支持INDIRECT级联的替代方案）
用户在子类下拉里一眼看出归属，选完带前缀。apply_review.py 会解析 '主类｜子类' 写法。"""
import json, subprocess

PY = "<python3>"
SKILL = "<user>/.workbuddy/plugins/cache/workbuddy-builtin/tencent-docs-plugin/5.5.4-wb.38151288.g1ca4889a.hde0fbd244c72/skills/tencent-docs"
FILE_ID = "YOUR_FILE_ID"
SHEET = "SHEET_6TgC25"
BASE = "<工作区目录>"

def call(tool, args):
    r = subprocess.run([PY, "tencentdocs.py", "tdoc_call", "sheet-mcp", tool, json.dumps(args, ensure_ascii=False)],
                       capture_output=True, text=True, cwd=SKILL, timeout=120)
    return r.stdout

recs = json.load(open(f"{BASE}/_v10_rows.json"))

PALETTE = ['#D6E5FF','#FFE6CC','#D9F2D9','#FDE7F3','#E8E0F8','#FFF2CC','#E0F0F0','#FADBD8','#E8E8E8',
           '#DDEBF7','#FCE4D6','#E2EFDA','#FCE4EC','#EDE7F6','#FFF9E6','#E0F2F1','#F9E79F','#D7BDE2']

def rebuild(key, col, label):
    pairs = {}
    for r in recs:
        pairs.setdefault(r[key][0], set()).add(r[key][1])
    order = sorted(pairs, key=lambda c: -sum(1 for r in recs if r[key][0] == c))
    color = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(order)}
    opts, idx = [], 0
    for c1 in order:
        for c2 in sorted(pairs[c1]):
            idx += 1
            opts.append({"id": str(idx), "text": f"{c1}｜{c2}", "bg_color": color[c1], "text_color": "#333333"})
    out = call("set_data_validation", {
        "file_id": FILE_ID, "sheet_id": SHEET, "type": "LIST",
        "col_indexes": [{"start": col, "end": col}], "ignore_rows": 1,
        "select_options": opts})
    ok = '"error"' not in out
    print(f"{label}(col{col}): {len(opts)}项 {'OK' if ok else out[:120]}")

rebuild('catGB', 11, 'GB子类')
rebuild('catQS', 13, 'QS子类')
rebuild('catZFB', 15, 'ZFB子类')
print("完成：子类选项格式=主类｜子类，同主类同底色分组")
