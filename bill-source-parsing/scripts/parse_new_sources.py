# -*- coding: utf-8 -*-
"""v5：整合配偶农行卡1(6228...1479) + 农行卡2(结息卡,忽略) + 配偶微信[温暖] + 支付宝待补"""
import openpyxl, json, re
from collections import defaultdict

BASE = "<工作区目录>"

# ============ 配偶微信（温暖） ============
wb = openpyxl.load_workbook(f"{BASE}/微信支付账单流水文件(20260301-20260928)_20260928120804.xlsx")
ws = wb["Sheet1"]
sp_wx = []
header = False
for row in ws.iter_rows(values_only=True):
    if row[0] == "交易时间":
        header = True; continue
    if not header or row[0] is None: continue
    sp_wx.append({"time": str(row[0]), "type": row[1], "counter": row[2] or "", "goods": row[3] or "",
                  "dir": row[4], "amt": float(row[5]), "pay": row[6] or "", "status": row[7] or ""})
print("配偶微信记录:", len(sp_wx))
json.dump(sp_wx, open(f"{BASE}/_spouse_wx.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 支付方式分布
paydist = defaultdict(lambda: [0, 0.0])
for r in sp_wx:
    if r["dir"] == "支出":
        paydist[r["pay"]][0] += 1
        paydist[r["pay"]][1] += r["amt"]
print("\n配偶微信支付方式分布:")
for p, (n, v) in sorted(paydist.items(), key=lambda x: -x[1][1]):
    print(f"  {p}: {n}笔 {v:,.2f}")

# ============ 农行卡1解析 ============
raw = open(f"{BASE}/农业银行-配偶卡1-20260928.txt", encoding="utf-8").read()
lines = [l.strip() for l in raw.splitlines() if l.strip()]
abc = []
i = 0
while i < len(lines):
    m = re.match(r"^(\d{8})\s+(\d{6})\s+(.+?)\s+([+-][\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+(.*)$", lines[i])
    if m:
        d, t, summary, amt, bal, rest = m.groups()
        # 对手信息可能折行到下几行（直至出现日志号样式的行）
        j = i + 1
        counter_extra = ""
        while j < len(lines) and not re.match(r"^\d{8}\s+\d{6}", lines[j]) and not lines[j].startswith(("户名", "币种", "起止", "交易日期", "该交易", "中国农业", "第")):
            counter_extra += lines[j]
            j += 1
        abc.append({"date": f"{d[:4]}-{d[4:6]}-{d[6:]}", "summary": summary, "amt": float(amt.replace(",", "")),
                    "counter_raw": (rest + counter_extra)[:80]})
        i = j
    else:
        i += 1
print("\n农行卡1记录数:", len(abc))
json.dump(abc, open(f"{BASE}/_spouse_abc.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 分类
FAMILY = {"本人", "配偶"}
def abc_class(r):
    s = r["counter_raw"] + r["summary"]
    if r["amt"] > 0: return "收入/内部"
    if "理财" in r["summary"]: return "投资/理财"
    if "妇幼" in s: return "医疗(宝宝/配偶)"
    if "XX医院" in s or "医院" in s: return "医疗(配偶手术相关)"
    if "社保" in r["summary"]: return "社保缴费"
    if "平安" in s: return "保险缴费(平安)"
    if "国库支付" in r["summary"] or "高级中学" in s: return "收入/内部"
    c = r["counter_raw"].split(" ")[0] if r["counter_raw"] else ""
    if c in FAMILY: return "家庭内部转账"
    if "微信转账" in s and r["amt"] <= -2000: return "大额微信转出-待确认"
    return "日常消费"

cat_agg = defaultdict(float)
for r in abc:
    r["cat"] = abc_class(r)
    if r["amt"] < 0:
        cat_agg[r["cat"]] += -r["amt"]
print("\n农行卡1支出分类:")
for k, v in sorted(cat_agg.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v:,.2f}")
print("\n大额微信转出明细:")
for r in abc:
    if r["cat"] == "大额微信转出-待确认":
        print(" ", r["date"], f"{-r['amt']:,.0f}", r["counter_raw"][:40])
print("\n医院相关支出:")
for r in abc:
    if "医疗" in r["cat"] and abs(r["amt"]) >= 100:
        print(" ", r["date"], f"{r['amt']:,.2f}", r["counter_raw"][:40].replace(chr(10), " "))
