# -*- coding: utf-8 -*-
"""解析招行借记卡流水：分类+按月汇总+生成9月逐笔明细"""
import re, json
from collections import defaultdict

TXT = "<工作区目录>"
raw = open(TXT, encoding="utf-8").read()

# 去掉页眉页脚
raw = re.sub(r"=====\sPAGE\s\d+\s=====", "", raw)
raw = re.sub(r"\d+/15", "", raw)
raw = re.sub(r"(记账日期|Date).{0,200}?(Counter Party|对手信息)", "", raw)
raw = re.sub(r"温馨提示：.*", "", raw, flags=re.S)
raw = re.sub(r"1、交易流水验真.*", "", raw, flags=re.S)

# 按记录切分
chunks = re.split(r"(?=\d{4}-\d{2}-\d{2}\s+CNY\s)", raw)
records = []
SUMMARIES = ["朝朝宝转出","朝朝宝转入","转账汇款","快捷支付","银联快捷支付","快捷退款",
             "汇入汇款","信用卡自动还款","信用卡还款","银证转账(第三方存管)","账户结息",
             "赎回","网联收款","行内转账转入","代发款项","养老金缴存"]
for c in chunks:
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s+CNY\s+(-?[\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})\s+(.*)", c.strip(), re.S)
    if not m:
        continue
    date, amt, bal, rest = m.group(1), float(m.group(2).replace(",","")), float(m.group(3).replace(",","")), " ".join(m.group(4).split())
    summary = ""
    for s in SUMMARIES:
        if s in rest:
            summary = s
            rest = rest.replace(s, " ", 1)
            break
    # 养老金缴存特殊：跨行拼接
    if "养老金缴存" in rest:
        summary = "养老金缴存"
        rest = rest.split("招行卡转入）")[0] if "招行卡转入）" in rest else rest
    counter = re.sub(r"Date\s+Currency.*?Counter\s+Party", " ", rest); counter = counter.replace("本人", "").strip(" ")
    records.append({"date": date, "amt": amt, "bal": bal, "summary": summary, "counter": counter})

print("解析记录数:", len(records))

# ============ 分类规则 ============
FAMILY = {"配偶","父亲","本人"}
INVEST_SUM = {"银证转账(第三方存管)","朝朝宝转入","赎回","养老金缴存","朝朝宝转出"}
INCOME_SUM = {"汇入汇款","代发款项","网联收款","账户结息","行内转账转入"}
CC_SUM = {"信用卡自动还款","信用卡还款"}
EXPENSE_SUM = {"快捷支付","银联快捷支付","转账汇款","快捷退款"}
BIG_UNKNOWN = {"种侠":"疑似租金(月付15,800/13,800,待确认)","婚宴商户":"大额转账,用途待确认","育儿嫂B":"大额转账,用途待确认"}
BIZ = {"创业合作方软件(深圳)有限公司","创业合作方软件（深圳）有限公司"}
INSUR_AGENT = {"母亲":"保险业务员(太平洋寿险),疑似保险保费,待确认"}
INVEST_LB = {"深圳前海办公房租商资产管理有限公司":"资产管理公司,疑似投资款,待确认"}

def classify(r):
    c, s, a = r["counter"], r["summary"], r["amt"]
    if s in INVEST_SUM: return "投资/理财申赎", ""
    if s in INCOME_SUM: return "收入", ""
    if s in CC_SUM: return "信用卡还款(账单已单列,勿重复计)", ""
    if s == "快捷退款" or (s == "银联快捷支付" and a > 0): return "退款", ""
    if c in FAMILY or c == "": return "家庭内部转账", ""
    if c in BIZ: return "创业往来(创业合作方)", ""
    if c == "母亲": return "保险缴款-待确认", INSUR_AGENT[c]
    if c in BIG_UNKNOWN: return ("大额待确认", BIG_UNKNOWN[c]) if abs(a) >= 2000 else ("日常消费", "")
    if c in INVEST_LB: return "投资款-待确认", INVEST_LB[c]
    if s in EXPENSE_SUM:
        if a < 0 and abs(a) >= 2000: return "大额消费", ""
        return "日常消费", ""
    return "其他", ""

for r in records:
    cat, note = classify(r)
    r["cat"], r["note"] = cat, note

# ============ 按月汇总 ============
monthly = defaultdict(lambda: defaultdict(float))
big_items = defaultdict(list)
for r in records:
    ym = r["date"][:7]
    monthly[ym][r["cat"]] += r["amt"]
    if r["cat"] in ("大额待确认","大额消费","保险缴款-待确认","投资款-待确认") and abs(r["amt"]) >= 2000:
        big_items[ym].append(f"{r['date'][5:]} {r['counter']} {r['amt']:,.0f}({r['cat']})")

print("\n=== 按月汇总（支出为负） ===")
print(f"{'月份':10s}{'日常消费':>12s}{'大额消费':>12s}{'大额待确认':>12s}{'保险待确认':>12s}{'投资待确认':>12s}{'退款':>10s}")
order = sorted(monthly)
for ym in order:
    d = monthly[ym]
    print(f"{ym:10s}{d.get('日常消费',0):>12,.2f}{d.get('大额消费',0):>12,.2f}{d.get('大额待确认',0):>12,.2f}{d.get('保险缴款-待确认',0):>12,.2f}{d.get('投资款-待确认',0):>12,.2f}{d.get('退款',0):>10,.2f}")

print("\n=== 各月大额明细 ===")
for ym in order:
    if big_items[ym]:
        print(ym, "; ".join(big_items[ym]))

print("\n=== 收入侧（工资等） ===")
sal = defaultdict(float)
for r in records:
    if r["cat"] == "收入" and r["amt"] > 0:
        sal[r["date"][:7]] += r["amt"]
for ym in order:
    if sal.get(ym): print(ym, f"收入合计 {sal[ym]:,.2f}")

# 2026-09 逐笔（供明细表）
sep = [r for r in records if r["date"] >= "2026-09-01"]
out = json.dumps(sep, ensure_ascii=False, indent=1)
open("<工作区目录>","w",encoding="utf-8").write(out)
print("\n9月逐笔", len(sep), "条已存 _cmb_sep.json")
print("期末余额:", records[-1]["bal"] if records else None)
