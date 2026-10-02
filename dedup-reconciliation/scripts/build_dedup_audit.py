# -*- coding: utf-8 -*-
"""统计所有去重/对冲规则的实际影响 → _dedup_audit.json
两类：
  visible   = 明细表中可见的冲减/对冲/排除行（负数或排除类别）
  invisible = 源头跳过的去重规则（表格中无对应行，最易出错）
"""
import json, csv, re
from collections import defaultdict

BASE = "<工作区目录>"
v7 = json.load(open(f"{BASE}/_v7_rows.json"))
data = v7[1:]

wx_me = json.load(open(f"{BASE}/_wechat_recs.json"))
wx_sp = json.load(open(f"{BASE}/_spouse_wx.json"))

def load_alipay(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hi = next(i for i, r in enumerate(rows) if r and r[0] == "交易时间")
    out = []
    for r in rows[hi+1:]:
        if len(r) >= 9 and r[0][:2] == "20":
            out.append({"time": r[0], "counter": r[2], "acct": r[3], "goods": r[4],
                        "dir": r[5], "amt": float(r[6]), "pay": r[7], "status": r[8]})
    return out
ali_me = load_alipay(f"{BASE}/本人支付宝.csv")
ali_sp = load_alipay(f"{BASE}/配偶支付宝.csv")

def active(r):
    return r["dir"] == "支出" and "退款成功" not in r["status"] and "交易关闭" not in r["status"]

# ===== 1. 可见对冲/排除行 =====
vis_cats = defaultdict(lambda: {"n": 0, "sum": 0, "rows": []})
for r in data:
    vis_cats[r[5]]["n"] += 1
    vis_cats[r[5]]["sum"] += float(r[6])
    vis_cats[r[5]]["rows"].append(r)

OFFSET_LABELS = {
    "退款": "冲减", "退款/冲销": "冲减", "资金过卡(排除)": "对冲",
    "内部转账(排除)": "对冲", "利息(排除)": "对冲", "保险理赔收入(排除)": "对冲",
    "伙食费收入(搭伙同事)-冲抵": "冲抵收入",
    "家人代存(妈妈)-not-expense": "排除", "家人代存/内部-排除": "排除", "已退回转账(搭伙同事)-排除": "排除",
    "信用卡账单周期汇总(9月)": "账单聚合",
}
visible = []
for cat, lab in OFFSET_LABELS.items():
    if cat in vis_cats:
        for row in vis_cats[cat]["rows"]:
            visible.append({
                "date": row[1], "owner": row[2], "acct": row[3], "counter": row[4],
                "cat": cat, "amt": float(row[6]), "type": lab,
                "note": row[9] if len(row) > 9 else "", "src": row[8] if len(row) > 8 else ""
            })

# ===== 2. 不可见去重规则 =====
def in_win(t, a, b): return a <= t[:10] <= b

def grab(recs, key, win=None):
    out = []
    for r in recs:
        if not active(r) or key not in r["pay"]: continue
        if win and not in_win(r["time"], *win): continue
        out.append({"date": r["time"][:10], "counter": str(r["counter"])[:20], "amt": float(r["amt"]),
                    "note": str(r["goods"])[:24] + " | " + str(r["status"])[:14]})
    return out

def rule(rid, title, why, items):
    return {"id": rid, "title": title, "why": why, "items": items,
            "n": len(items), "impact": round(sum(i["amt"] for i in items), 2)}

invisible = [
    rule("R01", "支付宝8551渠道 全跳过", "8551=9876招行储蓄卡老尾号（用户确认同一张卡），9876银行流水已含", grab(ali_me, "8551")),
    rule("R02", "支付宝6893渠道 全跳过", "6893=香港Pulse卡RMB子账户（云闪付），HK卡账单已含", grab(ali_me, "6893")),
    rule("R03", "配偶支付宝1479渠道 全跳过", "农行1479银行流水已含（同卡）", grab(ali_sp, "1479")),
    rule("R04", "微信2136渠道跳过 8/6-9/5", "该周期已由2136九月账单(PDF)整期计入", grab(wx_me, "(2136)", ("2026-08-06", "2026-09-05"))),
    rule("R05", "微信1298渠道跳过 8/10-9/9", "该周期已由1298九月账单整期计入", grab(wx_me, "(1298)", ("2026-08-10", "2026-09-09"))),
    rule("R06", "微信4738渠道跳过 8/23-9/22", "4738=7623附属卡，账单并入主卡7623", grab(wx_me, "(4738)", ("2026-08-23", "2026-09-22"))),
    rule("R07", "支付宝2136渠道跳过 8/6-9/5", "同R04，支付宝侧同卡", grab(ali_me, "2136", ("2026-08-06", "2026-09-05"))),
    rule("R08", "支付宝1298渠道跳过 8/10-9/9", "同R05，支付宝侧同卡", grab(ali_me, "1298", ("2026-08-10", "2026-09-09"))),
    rule("R09", "支付宝4738渠道跳过 8/23-9/22", "同R06，支付宝侧同卡", grab(ali_me, "4738", ("2026-08-23", "2026-09-22"))),
    rule("R10", "配偶微信7623渠道跳过 8/23-9/22", "该周期已由7623九月账单整期计入", grab(wx_sp, "7623", ("2026-08-23", "2026-09-22"))),
    rule("R11", "配偶支付宝7623渠道跳过 8/23-9/22", "同R10，支付宝侧同卡", grab(ali_sp, "7623", ("2026-08-23", "2026-09-22"))),
]

# 银行流水侧整类排除
EXCL_BANK_CATS = ["投资/理财申赎", "收入/内部流入", "信用卡还款(账单已单列)", "家庭内部转账", "创业往来(创业合作方)"]
prev = json.load(open(f"{BASE}/_mar_sep_summary.json"))["detail"]
bank_excl = []
for r in prev:
    if r["cat"] in EXCL_BANK_CATS:
        bank_excl.append({"date": r["date"], "counter": str(r.get("counter", ""))[:20], "amt": abs(r["amt"]),
                          "note": r.get("summary", "")[:18] + "|cat=" + r["cat"]})
invisible.append(rule("R12", "银行流水侧整类排除", "理财申赎/内部流入/信用卡还款/家庭内部转账/创业往来——非消费", bank_excl))

# 农行1479流水侧排除
abc = json.load(open(f"{BASE}/_spouse_abc.json"))
abc_excl = []
for r in abc:
    if r["amt"] > 0: continue
    summary = r.get("summary", "")
    counter = str(r.get("counter", r.get("counter_raw", "")))
    s = counter + summary
    tag = None
    if "理财" in summary or "结息" in summary: tag = "理财/结息"
    elif "国库支付" in summary: tag = "国库支付(公积金)"
    elif "转支" in summary and ("配偶" in s or "本人" in s): tag = "夫妻内部转账"
    elif "转支" in summary and "工资" in r.get("counter_raw", ""): tag = "工资户转支"
    if tag:
        abc_excl.append({"date": r["date"], "counter": counter[:20], "amt": abs(r["amt"]), "note": tag})
invisible.append(rule("R13", "农行1479流水侧排除", "理财/公积金/夫妻内部转账/工资户——非消费", abc_excl))

# 微信全额退款整笔跳过
wx_full_skip = []
for r in wx_me + wx_sp:
    if r["dir"] != "支出": continue
    if r["status"] and ("已全额退款" in r["status"] or "对方已退还" in r["status"]):
        wx_full_skip.append({"date": r["time"][:10], "counter": str(r["counter"])[:20], "amt": float(r["amt"]), "note": str(r["status"])[:16]})
invisible.append(rule("R14", "微信全额退款整笔跳过", "状态='已全额退款/对方已退还'→整笔不记", wx_full_skip))

# 微信部分退款扣减
wx_part = []
for r in wx_me + wx_sp:
    if r["dir"] != "支出": continue
    m = re.search(r"已退款\(¥([\d.]+)\)", r["status"] or "")
    if m:
        wx_part.append({"date": r["time"][:10], "counter": str(r["counter"])[:20], "amt": float(m.group(1)),
                        "note": str(r["status"])[:20] + " 原额" + str(r["amt"])})
invisible.append(rule("R15", "微信部分退款扣减", "状态含'已退款(¥X)'→按净额入账", wx_part))

# 支付宝退款/关闭跳过
ali_refund_skip = [{"date": r["time"][:10], "counter": str(r["counter"])[:20], "amt": float(r["amt"]), "note": str(r["status"])[:12]}
                   for r in ali_me + ali_sp if r["dir"] == "支出" and ("退款成功" in r["status"] or "交易关闭" in r["status"])]
invisible.append(rule("R16", "支付宝退款/关闭整笔跳过", "状态=退款成功/交易关闭→不记", ali_refund_skip))

# 零钱收入侧退款回冲不计
pk_in_skip = []
for r in wx_me + wx_sp:
    if r["dir"] == "收入" and r["pay"] == "零钱" and r["status"] and "已全额退款" in r["status"]:
        pk_in_skip.append({"date": r["time"][:10], "counter": str(r["counter"])[:20], "amt": float(r["amt"]), "note": "收入侧退款回冲"})
invisible.append(rule("R17", "微信零钱收入侧退款回冲不计", "退款回到零钱的收入行不计", pk_in_skip))

json.dump({"visible": visible, "invisible": invisible}, open(f"{BASE}/_dedup_audit.json", "w"), ensure_ascii=False, indent=1)

print("=== 可见对冲行（明细表内） ===")
for cat in OFFSET_LABELS:
    if cat in vis_cats:
        print(f"  [{OFFSET_LABELS[cat]}] {cat} | {vis_cats[cat]['n']}笔 | {vis_cats[cat]['sum']:,.2f}")
print("=== 不可见去重规则（源头跳过） ===")
for r in invisible:
    print(f"  {r['id']} {r['title']} | {r['n']}笔 | {r['impact']:,.2f}")
