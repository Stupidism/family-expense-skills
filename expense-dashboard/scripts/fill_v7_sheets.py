# -*- coding: utf-8 -*-
"""v7 灌数：把各源数据全量写入对应卡明细表（真相层，永不清空只追加）"""
import csv, io, json, subprocess, os, re
from collections import defaultdict

PY = "<python3>"
SKILL_DIR = "<user>/.workbuddy/plugins/cache/workbuddy-builtin/tencent-docs-plugin/5.5.4-wb.38151288.g1ca4889a.hde0fbd244c72/skills/tencent-docs"
os.chdir(SKILL_DIR)
FILE_ID = "YOUR_FILE_ID"
BASE = "<工作区目录>"
SM = json.load(open(f"{BASE}/_sheet_map.json"))

def call(tool, args):
    r = subprocess.run([PY, "tencentdocs.py", "tdoc_call", "sheet-mcp", tool, json.dumps(args, ensure_ascii=False)],
                       capture_output=True, text=True)
    return "trace_id" in r.stdout

def write_sheet(sid, header, rows):
    # 扩容检查
    need = len(rows) + 10
    subprocess.run([PY, "tencentdocs.py", "tdoc_call", "sheet-mcp", "insert_dimension",
                    json.dumps({"file_id": FILE_ID, "sheet_id": sid, "dimension_type": "row", "index": 199, "count": need})],
                   capture_output=True, text=True)
    data = [header] + rows
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([["" if c is None else c for c in r] for r in data])
    ok = call("set_range_value_by_csv", {"file_id": FILE_ID, "sheet_id": sid, "start_row": 0, "start_col": 0, "csv_data": buf.getvalue()})
    print(sid, "rows:", len(rows), "ok" if ok else "FAIL")

# ========== 原始记录重建（复用 parse_all.py 全量逻辑，3月起） ===========
SUMM = ["朝朝宝转出", "朝朝宝转入", "转账汇款", "快捷支付", "银联快捷支付", "快捷退款",
        "汇入汇款", "信用卡自动还款", "信用卡还款", "银证转账(第三方存管)", "账户结息",
        "赎回", "网联收款", "行内转账转入", "代发款项", "养老金缴存", "基金申购"]
CITIC_OUT = {"信用卡还款", "银行转账付款", "手机号转账", "网银互联跨行转出", "购买理财"}
recs_me, recs_sp = [], []
for src_name, out in [("me", recs_me), ("sp", recs_sp)]: pass

def parse_cmb_txt(txt_path):
    raw = open(txt_path, encoding="utf-8").read()
    raw = re.sub(r"=====\sPAGE\s\d+\s=====", "", raw)
    raw = re.sub(r"\d+/\d+", "", raw)
    raw = re.sub(r"(记账日期|Date).{0,200}?(Counter Party|对手信息)", "", raw)
    raw = re.sub(r"温馨提示：.*", "", raw, flags=re.S)
    out = []
    for c in re.split(r"(?=\d{4}-\d{2}-\d{2}\s+CNY\s)", raw):
        m = re.match(r"(\d{4}-\d{2}-\d{2})\s+CNY\s+(-?[\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})\s+(.*)", c.strip(), re.S)
        if not m: continue
        date = m.group(1); amt = float(m.group(2).replace(",", "")); rest = " ".join(m.group(4).split())
        summary = ""
        for s in SUMM:
            if s in rest: summary = s; rest = rest.replace(s, " ", 1); break
        counter = re.sub(r"Date\s+Currency.*?Counter\s+Party", " ", rest)
        counter = re.sub(r"\d{10,}", " ", counter).strip()
        counter = counter.replace("本人", "").replace("配偶", "").strip(" ")
        out.append({"date": date, "amt": amt, "summary": summary, "counter": counter})
    return out

me_all = [r for r in parse_cmb_txt(f"{BASE}/招商银行-本人借记卡-交易流水-20260923.txt") if r["date"] >= "2026-03-01"]
sp_all = [r for r in parse_cmb_txt(f"{BASE}/招商银行-配偶借记卡-交易流水-20260923.txt") if r["date"] >= "2026-03-01"]

H = ["日期", "摘要", "对手", "金额", "余额列忽略", "分类"]
rows = [[r["date"], r["summary"], r["counter"], r["amt"], "", ""] for r in me_all]
write_sheet(SM["卡明细-明招行9876"], H, rows)
rows = [[r["date"], r["summary"], r["counter"], r["amt"], "", ""] for r in sp_all]
write_sheet(SM["卡明细-配招行8316"], H, rows)

# 中信
import json as J
citic_raw = open(f"{BASE}/中信银行-账户明细-20260923.txt", encoding="utf-8").read()
crows = []
for line in citic_raw.splitlines():
    m = re.match(r"(\d{8})\s+RMB\s+([\d,]+\.\d{2})\s+RMB\s+([\d,]+\.\d{2})\s+(.*)", line.strip())
    if not m: continue
    s8 = m.group(1); date = f"{s8[:4]}-{s8[4:6]}-{s8[6:]}"
    first = float(m.group(2).replace(",", "")); rest = m.group(4)
    sm_m = re.match(r"[\u4e00-\u9fa5]+", rest)
    summary = sm_m.group(0) if sm_m else rest.split(" ")[0]
    c_m = re.search(r"[^\d\s]+$", rest)
    counter = c_m.group(0) if c_m else ""
    amt = -first if summary in CITIC_OUT else first
    crows.append([date, summary, counter, amt, "", ""])
write_sheet(SM["卡明细-明中信3829"], H, crows)

# 农行1479
abc = J.load(open(f"{BASE}/_spouse_abc.json"))
arows = [[r["date"], r["summary"], r["counter_raw"][:40], r["amt"], "", ""] for r in abc]
write_sheet(SM["卡明细-配农行1479"], H, arows)

# 微信渠道（双方）
wx_me = J.load(open(f"{BASE}/_wechat_recs.json"))
wx_sp = J.load(open(f"{BASE}/_spouse_wx.json"))
WH = ["交易时间", "类型", "对方", "商品", "收/支", "金额", "支付方式", "状态"]
wrows = [[str(r["time"])[:19], r["type"], r["counter"], r["goods"][:30], r["dir"], r["amt"], r["pay"], r["status"]] for r in wx_me]
write_sheet(SM["卡明细-明微信渠道"], WH, wrows)
wrows = [[str(r["time"])[:19], r["type"], r["counter"], r["goods"][:30], r["dir"], r["amt"], r["pay"], r["status"]] for r in wx_sp]
write_sheet(SM["卡明细-配微信渠道"], WH, wrows)

# 支付宝渠道（双方）
def load_alipay(fname):
    rows_ = list(csv.reader(open(f"{BASE}/{fname}", encoding="utf-8")))
    hi = next(i for i, r in enumerate(rows_) if r and r[0] == "交易时间")
    return rows_[hi+1:]
for fname, key in [("本人支付宝.csv", "卡明细-明支付宝渠道"), ("配偶支付宝.csv", "卡明细-配支付宝渠道")]:
    rows_ = [r for r in load_alipay(fname) if len(r) >= 9 and r[0][:2] == "20"]
    arow = [[r[0][:19], r[1], r[2], r[4][:30], r[5], r[6], r[7], r[8]] for r in rows_]
    write_sheet(SM[key], WH, arow)

# 中行保险（邮件来源，已知3笔+待扣）
ins = [["2026-08-31", "保险代扣", "太平洋寿险-爱无忧两全A款 第12期", -856.00, "", ""],
       ["2026-09-29", "保险代扣(待扣)", "太平洋寿险-爱相守定寿 第4期年交", -429.00, "", ""]]
write_sheet(SM["卡明细-明中行5436"], H, ins)
print("ALL DONE")
