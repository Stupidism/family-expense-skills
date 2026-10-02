# -*- coding: utf-8 -*-
"""微信账单解析：核对银行流水中"微信转账"大额的收款人 + 统计微信渠道开销"""
import openpyxl, json
from collections import defaultdict

wb = openpyxl.load_workbook("<工作区目录>)_20260923153600.xlsx")
ws = wb["Sheet1"]

recs = []
header_seen = False
for row in ws.iter_rows(values_only=True):
    if row[0] == "交易时间":
        header_seen = True
        continue
    if not header_seen or row[0] is None:
        continue
    recs.append({
        "time": row[0], "type": row[1], "counter": row[2] or "", "goods": row[3] or "",
        "dir": row[4], "amt": row[5], "pay": row[6] or "", "status": row[7] or "",
    })
print("微信记录数:", len(recs))

# ============ 1. 核对银行流水中的微信大额（3月3笔+8月3笔+4月2笔+7月1笔+9月1笔） ============
targets = [
    ("2026-03-02", 5080.00), ("2026-03-08", 3800.00), ("2026-03-26", 7628.00),
    ("2026-04-19", 2000.00), ("2026-08-16", 6000.00), ("2026-08-17", 5000.00),
    ("2026-08-29", 5100.00), ("2026-07-01", 2400.00), ("2026-09-01", 4224.00),
]
print("\n=== 大额微信转账核对（银行流水 → 微信账单） ===")
for d, amt in targets:
    hits = [r for r in recs if str(r["time"])[:10] == d and abs(float(r["amt"]) - amt) < 1.0 and r["dir"] == "支出"]
    if hits:
        for h in hits:
            print(f"{d} ¥{amt:,.0f} -> {h['counter']} ({h['type']}, {h['pay']}, 商品:{h['goods'][:20]})")
    else:
        # 放宽到±1天
        near = [r for r in recs if abs((r['time'] - __import__('datetime').datetime.strptime(d, '%Y-%m-%d')).days) <= 1 and r["dir"] == "支出" and abs(float(r["amt"]) - amt) < 1.0]
        if near:
            for h in near:
                print(f"{d} ¥{amt:,.0f} -> (±1天) {h['counter']} ({h['type']}, {h['pay']})")
        else:
            print(f"{d} ¥{amt:,.0f} -> 未找到（可能从非微信渠道/他人代付）")

# ============ 2. 微信渠道月度统计（仅支出，按支付方式） ============
print("\n=== 微信支付月度支出（按支付方式） ===")
monthly = defaultdict(lambda: defaultdict(float))
for r in recs:
    if r["dir"] != "支出": continue
    ym = str(r["time"])[:7]
    pay = r["pay"] or "未知"
    monthly[ym][pay] += float(r["amt"])
pays_all = sorted({p for d in monthly.values() for p in d})
print(f"{'月份':9s}" + "".join(f"{p[:14]:>16s}" for p in pays_all))
for ym in sorted(monthly):
    print(f"{ym:9s}" + "".join(f"{monthly[ym].get(p,0):>16,.0f}" for p in pays_all))

# ============ 3. 支付方式清单（判断与银行流水去重） ============
print("\n支付方式分布:", {p: sum(1 for r in recs if r['pay']==p and r['dir']=='支出') for p in pays_all})

json.dump(recs, open("<工作区目录>","w",encoding="utf-8"), ensure_ascii=False, default=str, indent=1)
print("\n已存 _wechat_recs.json")
