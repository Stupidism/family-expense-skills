# -*- coding: utf-8 -*-
"""给明细表 K-P 六列（三分类主类/子类）和 Q 列（事件）设置下拉单选，
用户改分类时点选即可，不用手打字。选项 = 当前数据里的实际值 + 字典表全量值。"""
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

def opts(values):
    """去重排序 → select_options"""
    vs = sorted(set(v for v in values if v))
    return [{"id": str(i+1), "text": v} for i, v in enumerate(vs)]

# 各列的选项集
gb_c1 = opts([r['catGB'][0] for r in recs] + ['食品烟酒','衣着','生活用品及服务'])
gb_c2 = opts([r['catGB'][1] for r in recs])
qs_c1 = opts([r['catQS'][0] for r in recs])
qs_c2 = opts([r['catQS'][1] for r in recs])
zfb_c1 = opts([r['catZFB'][0] for r in recs])
zfb_c2 = opts([r['catZFB'][1] for r in recs])
events = opts(['婚礼', '配偶手术及康复', '旅游', 'Deel离职', ''] )

print(f"GB主类{len(gb_c1)}项 / GB子类{len(gb_c2)} / QS主类{len(qs_c1)} / QS子类{len(qs_c2)} / ZFB主类{len(zfb_c1)} / ZFB子类{len(zfb_c2)}")

def set_list(col_start, col_end, options, label):
    out = call("set_data_validation", {
        "file_id": FILE_ID, "sheet_id": SHEET,
        "type": "LIST",
        "col_indexes": [{"start": col_start, "end": col_end}],
        "ignore_rows": 1,
        "select_options": options,
    })
    ok = '"error"' not in out
    print(f"{label} (col {col_start}-{col_end}): {'OK' if ok else out[:150]}")
    return ok

# K=GB主类(10) L=GB子类(11) M=QS主类(12) N=QS子类(13) O=ZFB主类(14) P=ZFB子类(15) Q=事件(16) R=复核(17)
set_list(10, 10, gb_c1, "GB主类")
set_list(11, 11, gb_c2, "GB子类")
set_list(12, 12, qs_c1, "QS主类")
set_list(13, 13, qs_c2, "QS子类")
set_list(14, 14, zfb_c1, "ZFB主类")
set_list(15, 15, zfb_c2, "ZFB子类")
# 事件列用多选（一笔可多事件）
out = call("set_data_validation", {
    "file_id": FILE_ID, "sheet_id": SHEET,
    "type": "MULTIPLE_LIST",
    "col_indexes": [{"start": 16, "end": 16}],
    "ignore_rows": 1,
    "select_options": events,
})
print(f"事件标签多选 (col 16): {'OK' if '\"error\"' not in out else out[:150]}")
# 复核列也加常用选项
review_opts = opts(['确认', '错误', 'GB主类=', 'GB子类=', 'QS主类=', 'ZFB主类='])
set_list(17, 17, review_opts, "复核快捷选项")
print("全部下拉设置完成")
