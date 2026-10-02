# -*- coding: utf-8 -*-
"""v10.5 信用卡账单聚合行 → 逐笔明细（按实际交易日期归月）
用户要求：8月的账单交易归8月、9月的归9月（不再整单塞进"9月"）

处理：
1) 删除2笔聚合行（2136: 4,576.25 / 7623: 14,123.46）
2) 2136九月账单（汇丰PDF已解密txt，周期8/6-9/5）→ 逐笔，剔除：
   - 手机还款 -3,634.94（还款，非消费，进对账台账思路但这里直接跳过）
   - 过卡大额：+N / -37,800 / -10,800 / -960（支付宝特约商户过卡，已有对冲组）
   - 退款负数行（与正消费对冲，如 -98/-34.23/-37.2）
   - 已在微信/支付宝渠道入账的交易（跳过窗口 8/6-9/5 内微信2136渠道的，但PDF里的支付宝通道交易
     与支付宝导出的"2136渠道"是同一笔——防重：PDF交易=支付宝/财付通通道，支付宝导出里也有！
     ★ 关键：支付宝导出只统计到 9/28，且 2136 渠道的支付宝交易在支付宝CSV里有（R07跳过窗口8/6-9/5）
     → PDF 里这些交易已在支付宝侧计过！但支付宝CSV只有"支付宝App发起"的交易，
     财付通通道（微信）的交易在微信侧。所以：PDF逐笔里只补"拼多多(特约)直接绑卡"类！
     精确防重规则：交易说明含 WLZF-支付宝 → 支付宝CSV已有；WLZF-财付通 → 微信账单已有（但微信导出止9/23）
     (特约)拼多多 = 卡直接通道，无渠道记录 → 补！
3) 7623九月账单（105笔，7623卡84笔+4738卡21笔）→ 已有防重（微信/支付宝渠道跳过8/23-9/22），
   但账单里美团支付/京东支付/支付宝-商户通道的交易微信/支付宝导出没有 → 这些是要补的！
   防重规则：merchant 以"美团支付/京东支付/支付宝-商户全名"且匹配日期+金额在v10已存在则跳过；
   微信渠道记录的（财付通-）对应微信导出已有——但微信导出止9/23！9/24-9/22的财付通交易需补
4) 逐笔按 trade_date 的月份归 ym（8月→2026年8月，9月→2026年9月）
"""
import json, re
from collections import defaultdict

BASE = "<工作区目录>"
recs = json.load(open(f"{BASE}/_v10_base.json"))

# ============ A. 解析 2136 九月账单 PDF txt ============
txt = open(f"{BASE}/汇丰中国信用卡-电子账单-202609-已解密.txt", encoding="utf-8").read()
hsbc = []
for line in txt.splitlines():
    # 08/05 08/06 WLZF-支付宝-江西省贝肽斯商贸有限 ￥16.90
    m = re.match(r"(\d{2})/(\d{2})\s+\d{2}/\d{2}\s+(.+?)￥(-?[\d,]+\.\d{2})$", line.strip())
    if not m: continue
    mo, day = int(m.group(1)), int(m.group(2))
    desc = m.group(3).strip()
    amt = float(m.group(4).replace(",", ""))
    year = 2026 if mo >= 3 else 2026  # 周期8/6-9/5
    hsbc.append({"date": f"2026-{mo:02d}-{day:02d}", "desc": desc, "amt": amt})

# 剔除规则
def hsbc_keep(t):
    d, desc, amt = t['date'], t['desc'], amt if False else t['amt']
    if '手机还款' in desc: return None, '还款'
    if '支付宝-特约商户' in desc: return None, '过卡资金(已有对冲组)'
    if amt < 0: return None, '退款(与原消费对冲)'
    return t, None

hsbc_add = []
hsbc_skip = defaultdict(float)
for t in hsbc:
    kept, why = hsbc_keep(t)
    if kept: hsbc_add.append(kept)
    else: hsbc_skip[why] += abs(t['amt'])

# 2136 防重：支付宝/财付通通道交易在渠道导出里已有（R04/R07跳过窗口就是为此）
hsbc_final = []
for t in hsbc_add:
    if 'WLZF-支付宝' in t['desc'] or 'WLZF-财付通' in t['desc']:
        hsbc_skip['渠道侧已有(支付宝/微信导出)'] += t['amt']
        continue
    # 只剩 (特约)拼多多 等卡直连通道
    hsbc_final.append(t)

# ============ B. 7623 九月账单逐笔 ============
cmb = json.load(open(f"{BASE}/_cmb_7623_bill_txns.json"))
recs_key = set()
for r in recs:
    recs_key.add((str(r['date'])[:10], round(abs(r['amt']), 2)))

cmb_final = []
cmb_skip = defaultdict(float)
for t in cmb:
    d, amt = t['trade_date'], abs(t['amt'])
    mc = t['merchant']
    # 4738附属卡：并入7623账单，微信侧8/23-9/22已跳过 → 账单侧要补吗？
    # v7规则：4738周期内跳过防双计（因为7623账单聚合行整期已计）→ 现在拆逐笔，4738也要逐笔补
    # 但微信渠道已有4738的记录被跳过了 → 补账单侧4738逐笔是对的
    # 防重：同日同额已在v10（渠道侧已有）→ 跳过
    if (d, round(amt, 2)) in recs_key:
        cmb_skip['渠道侧已有(同日同额)'] += t['amt']
        continue
    # 退款/冲正负数：金额为正是消费
    if t['amt'] > 0:
        cmb_skip['账单内退款冲正'] += t['amt']
        continue
    cmb_final.append(t)

# ============ C. 分类函数 ============
def classify(desc):
    s = str(desc)
    if any(k in s for k in ['铁路网络', '12306', '中铁']): return ('交通通信', '铁路出行')
    if any(k in s for k in ['电信']): return ('交通通信', '电信通讯')
    if any(k in s for k in ['沃尔玛', '钱大妈', '山姆']): return ('食品烟酒', '商超买菜')
    if any(k in s for k in ['麦当劳', '蜜雪冰城', '锅盔', '粥', '吴莊', '饭团', '冰室', '茶欢', '零食', '便利店', '易站', '赛壹', '超市', '卖场', '团购']): return ('食品烟酒', '餐饮外卖/零食')
    if any(k in s for k in ['哈啰', 'HELLO']): return ('交通通信', '打车/共享出行')
    if any(k in s for k in ['拼多多', '京东', '唯品会', '苏泊尔', '梦趣', '品牌购物卡', '药房', '大药房', '哈啰普惠', '贝肽斯', '萌宁', '一花一世', '今日卖场', '同路安信', '宽娱', '得恩', '翰博', '云途畅', '创誉空间', '海之宝', '邱集']): return ('生活用品及服务', '网购日用')
    if any(k in s for k in ['妇幼保健院', 'XX医院', '医院', '药房']): return ('医疗保健', '门诊药品')
    if any(k in s for k in ['美团', '象鲜']): return ('食品烟酒', '餐饮外卖')
    if '智者天下' in s: return ('教育文化娱乐', '知识付费(知乎)')
    if '管道燃气' in s: return ('居住', '水电燃气')
    if '贝肽' in s or '婴儿' in s or '玩具' in s: return ('婴儿用品', '用品')
    if any(k in s for k in ['沃尔玛购物卡', '蔡跃', '郑少霞']): return ('生活用品及服务', '网购日用')
    return ('生活用品及服务', '网购日用')

def to_qs(c1, c2):
    if c1 == '食品烟酒': return ('食品酒水', c2)
    if c1 == '交通通信': return ('行车交通' if c2 != '电信通讯' else '交流通讯', c2)
    if c1 == '生活用品及服务': return ('购物淘宝', '网购综合')
    if c1 == '医疗保健': return ('医疗保险', c2)
    if c1 == '居住': return ('居家物业', c2)
    if c1 == '教育文化娱乐': return ('休闲娱乐', c2)
    if c1 == '婴儿用品': return ('日常用品', '婴儿用品')
    return ('日常用品', '综合')

def to_zfb(c1, c2):
    if c1 == '食品烟酒': return ('餐饮美食', c2)
    if c1 == '交通通信': return ('交通出行' if c2 != '电信通讯' else '生活日用', c2)
    if c1 == '生活用品及服务': return ('购物消费', '网购综合')
    if c1 == '医疗保健': return ('医疗健康', c2)
    if c1 == '居住': return ('生活日用', c2)
    if c1 == '教育文化娱乐': return ('教育文化', c2)
    if c1 == '婴儿用品': return ('购物消费', '婴儿用品')
    return ('其他', '综合')

def mk_row(date, counter, amt, acct, owner, src, note=''):
    ym = f"{date[:4]}年{int(date[5:7])}月"
    c1, c2 = classify(counter)
    return {"ym": ym, "date": date, "owner": owner, "acct": acct, "counter": str(counter)[:22],
            "cat": "信用卡账单逐笔", "cat1": c1, "cat2": c2,
            "catGB": [c1, c2], "catQS": list(to_qs(c1, c2)), "catZFB": list(to_zfb(c1, c2)),
            "event": [], "amt": round(abs(amt), 2), "src": src, "note": note, "review": ""}

new_rows = []
# 2136 逐笔（含直连通道）
for t in hsbc_final:
    desc = t['desc'].replace('WLZF-', '').replace('（特约）', '')
    new_rows.append(mk_row(t['date'], desc, t['amt'], '汇丰信用卡-2136(逢)', '逢', '汇丰账单PDF', '账单逐笔拆分v10.5'))
# 7623/4738 逐笔
for t in cmb_final:
    acct = '招行信用卡-7623(暖)' if t['card'] == '7623' else '招行信用卡-4738(逢附属卡)'
    owner = '暖' if t['card'] == '7623' else '逢'
    new_rows.append(mk_row(t['trade_date'], t['merchant'], t['amt'], acct, owner, '招行账单eml', '账单逐笔拆分v10.5'))

# ============ D. 替换聚合行 ============
removed = [r for r in recs if r['cat1'] == '信用卡账单聚合']
removed_amt = sum(r['amt'] for r in removed)
recs = [r for r in recs if r['cat1'] != '信用卡账单聚合']
recs += new_rows
recs.sort(key=lambda x: (str(x['date'])[:10], -abs(x['amt'])))
json.dump(recs, open(f"{BASE}/_v10_base.json", 'w'), ensure_ascii=False, indent=1)

added_amt = sum(r['amt'] for r in new_rows)
print(f"删除聚合行: {len(removed)}笔 -{removed_amt:,.2f}")
print(f"新增逐笔: {len(new_rows)}笔 +{added_amt:,.2f}（2136直连{len(hsbc_final)} + 7623/4738渠道缺失{len(cmb_final)}）")
print(f"剔除明细: {dict((k, round(v,2)) for k,v in hsbc_skip.items())}")
print(f"7623剔除: {dict((k, round(v,2)) for k,v in cmb_skip.items())}")
EXCL = {'家人代存(妈妈)-not-expense','家人代存/内部-排除','已退回转账(搭伙同事)-排除'}
net = sum(r['amt'] for r in recs if r['cat'] not in EXCL)
print(f"净额: {net:,.2f}（原N → 差 {net-462382.23:,.2f}）")
# 按月分布变化
mm = defaultdict(float)
for r in recs:
    if r['cat'] not in EXCL: mm[r['ym']] += r['amt']
for k in sorted(mm): print(f"  {k}: {mm[k]:,.2f}")
