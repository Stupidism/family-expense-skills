# -*- coding: utf-8 -*-
"""v10 对账标注系统：
原则（用户定）：
  1. 不给流水明细加"对冲行"——一加一减的对账用 S/T 列标注（对冲组ID + 类型）
  2. 退款/过卡负数行：能配对原消费的 → 原行标"已对冲组N"，负数行不进主明细（进对账台账）
  3. 微信转账+退回（搭伙同事4笔）→ 左右对称对账
  4. 储蓄卡出账 ↔ 信用卡入账（还款）→ 对账组
  5. 支付渠道流水 ↔ 银行卡扣费 → 银行侧标"渠道已记"（支付宝侧数据更详细优先）
  6. 部分退款 → 明细里保留两行，都标注同一对冲组
输出 _v10_rows.json：每行加 offsetGroup / offsetType / reconRole 字段
      _v10_recon.json：对账台账（左右对称结构，供仪表盘对账视图）
"""
import json, re
from collections import defaultdict

BASE = "<工作区目录>"
v9 = json.load(open(f"{BASE}/_v10_base.json"))

# ============================================================
# A. 全量配对引擎：在 v9 全集里找 退款负数行 ↔ 正数消费行
#    覆盖：银行退款/微信退款负行/账单内负数/过卡
# ============================================================
gid = 0
recon = []          # 对账台账 [{gid, type, left:[...], right:[...], note}]
recs = v9

def find_match(neg_idx, used):
    """给负数行找配对正数行：金额相等 + (counter匹配 或 日期临近)"""
    nr = recs[neg_idx]
    target = round(-nr['amt'], 2)
    # 1) 同counter精确
    for pi in range(len(recs)):
        if pi in used or pi == neg_idx: continue
        pr = recs[pi]
        if round(pr['amt'], 2) != target or pr['amt'] <= 0: continue
        if pr['counter'] == nr['counter']: return pi
    # 2) counter 包含 或 金额近似+前后14天内同渠道
    for pi in range(len(recs)):
        if pi in used or pi == neg_idx: continue
        pr = recs[pi]
        if pr['amt'] <= 0: continue
        diff = round(pr['amt'], 2) - target
        if abs(diff) > 2: continue
        same_channel = (pr['acct'][:6] == nr['acct'][:6]) or ('微信' in pr['acct'] and '微信' in nr['acct'])
        try:
            dd = abs((pr['date'][:10] if len(pr['date'])>=10 else pr['date']) > (nr['date'][:10] if len(nr['date'])>=10 else nr['date']))
            nd, pd = nr['date'][:10], pr['date'][:10]
            near = abs((int(nd[8:10]) - int(pd[8:10]))) <= 14 if nd[:7] == pd[:7] else False
        except Exception:
            near = False
        if (nr['counter'] and (nr['counter'] in pr['counter'] or pr['counter'] in nr['counter'])) and same_channel:
            return pi
        if same_channel and near and abs(diff) <= 0.01:
            return pi
    return None

used = set()
pairs = []  # (neg_idx, pos_idx)
for ni in range(len(recs)):
    nr = recs[ni]
    if nr['amt'] >= 0: continue
    # 只对冲明确的退款类（不动负数的其他情形——v9里负数基本都是退款）
    if nr['cat1'] not in ('退款/对冲', '资金过卡'): continue
    mi = find_match(ni, used)
    if mi is not None:
        used.add(mi)
        pairs.append((ni, mi))

# 写标注
for ni, pi in pairs:
    gid += 1
    gname = f"G{gid:03d}"
    recs[ni]['offsetGroup'] = gname
    recs[ni]['offsetType'] = '退款冲销'
    recs[ni]['reconRole'] = 'credit'   # 入账方（钱回来）
    recs[ni]['_hide'] = True           # 负数行不进主明细视图
    recs[pi]['offsetGroup'] = gname
    recs[pi]['offsetType'] = '退款冲销'
    recs[pi]['reconRole'] = 'debit'
    recon.append({'gid': gname, 'type': '退款冲销',
                  'left': recs[ni], 'right': recs[pi],
                  'note': f"{recs[ni]['date']} {recs[ni]['counter'][:14]} {recs[ni]['amt']:.2f} ↔ 原消费"})

# ============================================================
# B. 搭伙同事4笔（微信转账+退回，2026-04-19/20）——已在v7数据里是"已退回-排除"4行
#    把它们改成对账组（左右对称：2笔转账出 vs 2笔退回入）
# ============================================================
zg_debit = [i for i, r in enumerate(recs) if '搭伙同事' in str(r['counter']) and r['amt'] > 0 and '已退回' in r['cat']]
zg_credit = [i for i, r in enumerate(recs) if r['amt'] < 0 and ('搭伙同事' in str(r['counter']) or '退款' in str(r['counter'])) and '已退回' in r['cat']]
if zg_debit and zg_credit:
    gid += 1
    gname = f"G{gid:03d}"
    for i in zg_debit + zg_credit:
        recs[i]['offsetGroup'] = gname
        recs[i]['offsetType'] = '转账退回'
        recs[i]['reconRole'] = 'credit' if recs[i]['amt'] < 0 else 'debit'
        recs[i]['_hide'] = True
    recon.append({'gid': gname, 'type': '转账退回',
                  'left': [recs[i] for i in zg_credit], 'right': [recs[i] for i in zg_debit],
                  'note': '微信转账2000×2 ↔ 退回2000×2（搭伙同事，4/19-4/20）'})

# ============================================================
# C. 储蓄卡还款 ↔ 信用卡账单（银行流水侧：信用卡自动还款-454 等）
#    v9里这些行在"信用卡账单聚合"或被排除类里吗？——自动还款在R12排除清单里（银行侧）
#    处理：从 R12 审计数据恢复这些行进对账台账（不进主明细）
# ============================================================
dedup = json.load(open(f"{BASE}/_dedup_audit.json"))
r12 = next(r for r in dedup['invisible'] if r['id'] == 'R12')
cc_repay = [i for i in r12['items'] if '信用卡' in i['note']]
for it in cc_repay:
    gid += 1
    gname = f"G{gid:03d}"
    recon.append({'gid': gname, 'type': '信用卡还款',
                  'left': {'date': it['date'], 'counter': '信用卡账单(应还入账)', 'amt': -it['amt'], 'acct': it['counter'][:20]},
                  'right': {'date': it['date'], 'counter': it['counter'][:20], 'amt': it['amt'], 'acct': '储蓄卡出账'},
                  'note': f"储蓄卡-{'{:,}'.format(it['amt'])} ↔ 信用卡+{'{:,}'.format(it['amt'])}（还款，非消费，双向都不计开销）"})

# 信用卡账单聚合行（18,699.71那2行）标记对账类型
for r in recs:
    if r['cat1'] == '信用卡账单聚合':
        r['offsetType'] = '信用卡账单(防漏行)'
        r['_hide'] = False   # 保留显示但可识别

# ============================================================
# D. 渠道↔银行双记（支付宝扣123 + 银行卡流水123）：
#    v7去重规则已在源头跳过（R01/R02/R03等），这里把这些规则转化为"渠道优先"对账条目
# ============================================================
for rule in dedup['invisible']:
    if rule['id'] in ('R01', 'R02', 'R03', 'R04', 'R06', 'R07', 'R09', 'R10', 'R11'):
        for it in rule['items']:
            gid += 1
            gname = f"G{gid:03d}"
            recon.append({'gid': gname, 'type': '渠道/银行双记(银行侧免记)',
                          'left': {'date': it['date'], 'counter': it['counter'][:18], 'amt': it['amt'], 'acct': '支付渠道侧(已采用，分类更准)'},
                          'right': {'date': it['date'], 'counter': it['counter'][:18], 'amt': it['amt'], 'acct': f"银行/账单侧(免记·{rule['id']})"},
                          'note': rule['title']})

# ============================================================
# E. 部分退款：R15审计数据（16笔"已退款(¥X)"→净额入账已是单行），
#    在明细行备注列已有信息。这里给这些行打部分退款标
# ============================================================
r15 = next(r for r in dedup['invisible'] if r['id'] == 'R15')
part_marks = {(it['date'], round(it['amt'], 2)) for it in r15['items']}
for r in recs:
    if (r['date'], ) and any(r['date'] == d and abs(r['amt']) >= a for d, a in part_marks):
        r['offsetType'] = r.get('offsetType') or '含部分退款(净额)'
        r['partialRefund'] = True

# 保存
json.dump(recs, open(f"{BASE}/_v10_rows.json", 'w'), ensure_ascii=False, indent=1)
# 对账台账精简（left/right 只存关键字段）
def slim(r):
    if isinstance(r, dict):
        return {'date': r.get('date'), 'counter': str(r.get('counter'))[:18], 'amt': r.get('amt'), 'acct': str(r.get('acct'))[:16]}
    return r
for g in recon:
    if isinstance(g.get('left'), list):
        g['left'] = [slim(x) for x in g['left']]
        g['right'] = [slim(x) for x in g['right']]
    else:
        g['left'] = slim(g['left']); g['right'] = slim(g['right'])
json.dump(recon, open(f"{BASE}/_v10_recon.json", 'w'), ensure_ascii=False, indent=1)

# ===== 汇总 =====
from collections import Counter
tc = Counter(g['type'] for g in recon)
print("对账组总数:", len(recon))
for t, n in tc.items(): print(f"  {t}: {n}")
paired_main = [r for r in recs if r.get('offsetGroup')]
hidden = [r for r in recs if r.get('_hide')]
print(f"主明细标注对冲: {len(paired_main)} 行（其中隐藏 {_hide_count if (_hide_count:=len(hidden)) else 0} 行）")
net = sum(r['amt'] for r in recs if r['cat'] not in ('家人代存(妈妈)-not-expense', '家人代存/内部-排除', '已退回转账(搭伙同事)-排除'))
print(f"净额: {net:,.2f}（应N）")
