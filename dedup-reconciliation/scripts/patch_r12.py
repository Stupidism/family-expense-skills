# -*- coding: utf-8 -*-
"""恢复 R12（银行流水侧整类排除）明细：重跑 parse_all 的解析，抓被过滤的行"""
import re, json, sys
sys.path.insert(0, "<工作区目录>")

BASE = "<工作区目录>"

# ---- 复用 parse_all 的解析函数（不执行其主流程，手动import函数）----
FAMILY = {"配偶", "父亲", "本人", ""}
INVEST_SUM = {"银证转账(第三方存管)", "朝朝宝转入", "赎回", "养老金缴存", "朝朝宝转出", "基金申购", "理财清盘返款", "购买理财", "对私定期到期结清"}
INCOME_SUM = {"汇入汇款", "代发款项", "网联收款", "账户结息", "行内转账转入", "批量结息入账", "跨行转入", "手机号转账"}
CC_SUM = {"信用卡自动还款", "信用卡还款", "二代支付"}
KNOWN = {
    "婚宴商户": "婚宴酒席", "育儿嫂B": "育儿嫂工资",
    "深圳前海办公房租商资产管理有限公司": "创业房租",
    "北京旅行社国际旅行社有限公司": "孝亲旅游(岳父母)",
    "北京旅行社国际旅行社有限公 司": "孝亲旅游(岳父母)",
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

me = parse_cmb(f"{BASE}/招商银行-本人借记卡-交易流水-20260923.txt")
spouse = parse_cmb(f"{BASE}/招商银行-配偶借记卡-交易流水-20260923.txt")
citic = parse_citic(f"{BASE}/中信银行-账户明细-20260923.txt")

EXCL = ["投资/理财申赎", "收入/内部流入", "信用卡还款(单列)", "家庭内部转账", "创业往来(创业合作方)"]
bank_excl = []
for src, recs in [("本人招行9876", me), ("配偶招行8316", spouse), ("中信3829", citic)]:
    for r in recs:
        if r["date"] < "2026-03-01": continue
        cat = classify(r["summary"], r["counter"], r["amt"], r.get("date", ""))
        if cat in EXCL:
            bank_excl.append({"date": r["date"], "counter": (src + "→" + (r["counter"] or "(本人他卡)"))[:26],
                              "amt": abs(r["amt"]), "note": (r["summary"] + "|cat=" + cat)[:26]})

# 更新 _dedup_audit.json 的 R12
aud = json.load(open(f"{BASE}/_dedup_audit.json"))
for rule in aud["invisible"]:
    if rule["id"] == "R12":
        rule["items"] = bank_excl
        rule["n"] = len(bank_excl)
        rule["impact"] = round(sum(i["amt"] for i in bank_excl), 2)
        rule["why"] = "理财申赎/收入流入/信用卡还款/家庭内部转账/创业往来——非消费性资金流动"
json.dump(aud, open(f"{BASE}/_dedup_audit.json", "w"), ensure_ascii=False, indent=1)

from collections import Counter
print("R12 恢复:", len(bank_excl), "笔 |", f"{sum(i['amt'] for i in bank_excl):,.2f}")
for cat, n in Counter(i["note"].split("cat=")[1] for i in bank_excl).items():
    s = sum(i["amt"] for i in bank_excl if f"cat={cat}" in i["note"])
    print(f"  {cat}: {n}笔 {s:,.2f}")
