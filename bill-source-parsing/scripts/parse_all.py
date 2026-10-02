# -*- coding: utf-8 -*-
"""三源账单统一解析：
1) 本人招行 2) 配偶招行 3) 中信银行
口径：2026-03 起；分类确认：婚宴商户=婚宴、育儿嫂B=育儿嫂、办公房租商=创业房租、旅行社=岳父母旅游
"""
import re, json
from collections import defaultdict

BASE = "<工作区目录>"

# ============ 共用分类 ============
FAMILY = {"配偶", "父亲", "本人", ""}   # 本人+空=本人他卡
INVEST_SUM = {"银证转账(第三方存管)", "朝朝宝转入", "赎回", "养老金缴存", "朝朝宝转出", "基金申购", "理财清盘返款", "购买理财", "对私定期到期结清"}
INCOME_SUM = {"汇入汇款", "代发款项", "网联收款", "账户结息", "行内转账转入", "批量结息入账", "跨行转入", "手机号转账"}
CC_SUM = {"信用卡自动还款", "信用卡还款", "二代支付"}
KNOWN = {
    "婚宴商户": "婚宴酒席",
    "育儿嫂B": "育儿嫂工资",
    "深圳前海办公房租商资产管理有限公司": "创业房租",
    "北京旅行社国际旅行社有限公司": "孝亲旅游(岳父母)", "北京旅行社国际旅行社有限公 司": "孝亲旅游(岳父母)",
    "种侠": "历史房租(已停)",
    "创业合作方软件(深圳)有限公司": "创业往来(创业合作方)",
    "创业合作方软件（深圳）有限公司": "创业往来(创业合作方)",
    "母亲428": "婚礼支出", "母亲": "家人往来", "缪鸿发": "待确认",
    "育儿嫂C": "育儿嫂工资",
}

def classify(summary, counter, amt, date=""):
    if summary in INVEST_SUM: return "投资/理财申赎"
    if summary in INCOME_SUM: return "收入/内部流入"
    if summary in CC_SUM: return "信用卡还款(单列)"
    if summary in INCOME_SUM and summary not in CC_SUM: return "收入/内部流入"
    if amt > 0 or summary in ("快捷退款",): return "退款"
    if counter in FAMILY: return "家庭内部转账"
    if counter == "母亲":
        return "婚宴酒席" if date == "2026-04-28" else "家人代存(妈妈)-not-expense"
    if counter in KNOWN:
        tag = KNOWN[counter]
        return tag if tag != "待确认" else "待确认支出"
    if abs(amt) >= 2000: return "大额支出"
    return "日常消费"

def parse_cmb(txt_path):
    raw = open(txt_path, encoding="utf-8").read()
    raw = re.sub(r"=====\sPAGE\s\d+\s=====", "", raw)
    raw = re.sub(r"\d+/\d+", "", raw)
    raw = re.sub(r"(记账日期|Date).{0,200}?(Counter Party|对手信息)", "", raw)
    raw = re.sub(r"温馨提示：.*", "", raw, flags=re.S)
    SUMM = ["朝朝宝转出", "朝朝宝转入", "转账汇款", "快捷支付", "银联快捷支付", "快捷退款",
            "汇入汇款", "信用卡自动还款", "信用卡还款", "银证转账(第三方存管)", "账户结息",
            "赎回", "网联收款", "行内转账转入", "代发款项", "养老金缴存", "基金申购"]
    recs = []
    for c in re.split(r"(?=\d{4}-\d{2}-\d{2}\s+CNY\s)", raw):
        m = re.match(r"(\d{4}-\d{2}-\d{2})\s+CNY\s+(-?[\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})\s+(.*)", c.strip(), re.S)
        if not m: continue
        date = m.group(1); amt = float(m.group(2).replace(",", "")); rest = " ".join(m.group(4).split())
        summary = ""
        for s in SUMM:
            if s in rest:
                summary = s; rest = rest.replace(s, " ", 1); break
        counter = re.sub(r"Date\s+Currency.*?Counter\s+Party", " ", rest); counter = re.sub(r"\d{10,}", " ", counter).strip()
        counter = counter.replace("本人", "").replace("配偶", "").strip(" ")
        recs.append({"date": date, "amt": amt, "summary": summary, "counter": counter})
    return recs

CITIC_OUT = {"信用卡还款", "银行转账付款", "手机号转账", "网银互联跨行转出", "购买理财"}

def parse_citic(txt_path):
    """中信两栏式：PDF折叠空列后每行为 [日期 RBM 首个非空金额 RMB 余额 摘要...对方]，
    方向按摘要词判断：OUTFLOW 集合 -> 支出(负)，否则收入(正)。"""
    raw = open(txt_path, encoding="utf-8").read()
    recs = []
    for line in raw.splitlines():
        m = re.match(r"(\d{8})\s+RMB\s+([\d,]+\.\d{2})\s+RMB\s+([\d,]+\.\d{2})\s+(.*)", line.strip())
        if not m: continue
        s = m.group(1); date = f"{s[:4]}-{s[4:6]}-{s[6:]}"
        first = float(m.group(2).replace(",", ""))
        rest = m.group(4)
        sm_m = re.match(r"[\u4e00-\u9fa5]+", rest)
        summary = sm_m.group(0) if sm_m else rest.split(" ")[0]
        counter_m = re.search(r"[^\d\s]+$", rest)
        counter = counter_m.group(0) if counter_m else ""
        amt = -first if summary in CITIC_OUT else first
        recs.append({"date": date, "amt": amt, "summary": summary, "counter": counter})
    return recs

# ============ 解析三源 ============
me = parse_cmb(f"{BASE}/招商银行-本人借记卡-交易流水-20260923.txt")
spouse = parse_cmb(f"{BASE}/招商银行-配偶借记卡-交易流水-20260923.txt")
citic = parse_citic(f"{BASE}/中信银行-账户明细-20260923.txt")
print("记录数 本人招行", len(me), "配偶招行", len(spouse), "中信", len(citic))

sources = [("本人招行", me), ("配偶招行", spouse), ("中信", citic)]
monthly = defaultdict(lambda: defaultdict(float))
flagged = []
for src, recs in sources:
    for r in recs:
        if r["date"] < "2026-03-01": continue
        r["cat"] = classify(r["summary"], r["counter"], r["amt"], r.get("date",""))
        r["src"] = src
        ym = r["date"][:7]
        monthly[ym][f"{src}|{r['cat']}"] += r["amt"]
        if r["cat"] in ("待确认支出", "大额支出", "保险相关待确认") and r["amt"] <= -2000:
            flagged.append(r)

print("\n=== 月度开销汇总（2026-03 起，支出为负） ===")
CATS = ["日常消费", "婚宴酒席", "育儿嫂工资", "创业房租", "孝亲旅游(岳父母)", "大额支出", "待确认支出"]
print(f"{'月份':9s}" + "".join(f"{c[:6]:>10s}" for c in CATS) + f"{'退款':>9s}{'合计净支出':>11s}")
result = {}
for ym in sorted(monthly):
    d = monthly[ym]
    row = {}
    total = 0
    for cat in CATS + ["退款"]:
        v = sum(d.get(f"{s}|{cat}", 0) for s, _ in sources)
        row[cat] = round(v, 2)
        if cat != "退款": total += v
    row["净支出"] = round(total + row["退款"], 2)
    result[ym] = row
    print(f"{ym:9s}" + "".join(f"{row[c]:>10,.0f}" for c in CATS) + f"{row['退款']:>9,.0f}{row['净支出']:>11,.0f}")

print("\n=== 待确认/大额明细 ===")
for r in flagged:
    print(f"{r['date']} [{r['src']}] {r['counter'] or '(空)'} {r['amt']:,.2f} {r['summary']} -> {r['cat']}")

alldetail = []
for src_name, recs in sources:
    for r in recs:
        if r["date"] >= "2026-03-01" and r["cat"] not in ("投资/理财申赎", "收入/内部流入", "信用卡还款(单列)", "家庭内部转账", "创业往来(创业合作方)"):
            alldetail.append(r)
json.dump({"detail": alldetail, "monthly": {k: v for k, v in result.items()},
           "flagged": flagged}, open(f"{BASE}/_mar_sep_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("\n已存 _mar_sep_summary.json")
