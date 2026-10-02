# -*- coding: utf-8 -*-
"""v8 重分类引擎：
1. 主类 = 国家统计局《居民消费支出》八大类（食品烟酒/衣着/居住/生活用品及服务/交通通信/
   教育文化娱乐/医疗保健/其他用品及服务）
2. 八大类套不进的 → 自定义扩展类（按统计局"转移性支出/经营性支出/偿债与财富"框架）：
   家庭服务(育儿嫂)｜孝亲馈赠｜婚礼专项｜生育专项｜保险保障｜创业经营｜房贷月供｜投资理财申赎｜亲情往来(非消费)
3. 事件标签（多维度，一笔可多标签）：婚礼｜配偶手术｜旅游｜Deel离职
4. 补录：房贷7笔(8316→工行MORTGAGE_ACCT_NO)
5. 对冲配对：退款负数行 ↔ 原消费正数行（配对后显示删除线）
输出：_v8_rows.json（含 cat1主类/cat2子类/event/tag/pairId 字段）
"""
import json, re
from collections import defaultdict

BASE = "<工作区目录>"
v7 = json.load(open(f"{BASE}/_v7_rows.json"))
header, data = v7[0], v7[1:]

# ============ 旧分类 → 新分类映射（cat1 八大类+扩展 / cat2 子类）============
# 沿用旧cat精确匹配；counter/note 关键词补充判断在后置规则里
CAT_MAP = {
    # ---- 食品烟酒 ----
    '伙食费(父亲代买)': ('食品烟酒', '伙食买菜(父亲经手)'),
    '餐饮': ('食品烟酒', '餐饮外卖'),
    # ---- 居住 ----
    '家庭公共事业费': ('居住', '水电燃气'),
    '创业房租': ('创业经营', '办公房租'),   # 创业用房租→创业经营
    '汽车费用(停车物业)': ('居住', '停车物业'),
    # ---- 交通通信 ----
    '交通出行': ('交通通信', '铁路出行'),
    '通讯费': ('交通通信', '电信通讯'),
    # ---- 教育文化娱乐 ----
    '宝宝早教': ('教育文化娱乐', '宝宝早教'),
    '订阅服务': ('教育文化娱乐', '数字订阅'),
    '网购/订阅': ('教育文化娱乐', '数字订阅'),
    # ---- 医疗保健 ----
    '医疗(宝宝宝宝)': ('医疗保健', '宝宝医疗'),
    '医疗(配偶手术)-待保险报销': ('医疗保健', '配偶手术(待报销)'),
    '医疗(配偶手术相关)': ('医疗保健', '配偶手术(待报销)'),
    '陪护(配偶手术)-待保险报销': ('医疗保健', '陪护(配偶手术)'),
    '育儿服务': ('医疗保健', '母婴护理'),
    '产后康复(产后康复师)': ('医疗保健', '产后康复'),
    '孝亲医疗(父亲)': ('医疗保健', '父亲医疗'),
    '心理咨询': ('医疗保健', '心理咨询'),
    # ---- 其他用品及服务 ----
    '日常消费': ('其他用品及服务', '综合消费(未细分)'),
    '日常消费(零钱渠道汇总)': ('其他用品及服务', '零钱渠道汇总'),
    '日常消费(配偶零钱汇总)': ('其他用品及服务', '零钱渠道汇总'),
    '日常采购': ('生活用品及服务', '日用采购'),
    '爱心公益': ('其他用品及服务', '公益捐赠'),   # 用户确认爱心助学算开销
    # ---- 扩展类 ----
    '育儿嫂工资': ('家庭服务(育儿嫂)', '育儿嫂工资'),
    '阿姨工资': ('家庭服务(育儿嫂)', '阿姨/育儿嫂工资'),
    '婚宴酒席': ('婚礼专项', '婚宴酒席'),
    '婚宴酒席(妈妈经手)': ('婚礼专项', '婚宴酒席(妈妈经手)'),
    '婚礼-金条(用户确认)': ('婚礼专项', '金条'),
    '婚礼-酒店(用户确认)': ('婚礼专项', '婚房酒店'),
    '孝亲旅游(岳父母)': ('孝亲馈赠', '岳父母旅游'),
    '孝亲(岳母)': ('孝亲馈赠', '岳母'),
    '孝亲支出(岳父)': ('孝亲馈赠', '岳父'),
    '礼品(大闸蟹礼券)': ('孝亲馈赠', '节礼(蟹券)'),
    '家庭旅游(4月银联大额待确认)': ('婚礼专项', '4月银联大额(已确认婚礼相关)'),
    '大额支出': ('其他用品及服务', '大额(待细分)'),
    '社保缴费': ('保险保障', '社保'),
    '保险-爱无忧': ('保险保障', '寿险(爱无忧)'),
    '保险-爱无忧两全A款': ('保险保障', '寿险(爱无忧)'),
    '保险-爱相守定寿年交': ('保险保障', '定寿(爱相守)'),
    '保险缴费(平安)': ('保险保障', '平安保险'),
    '保险': ('保险保障', '其他保险'),
    '创业经营支出': ('创业经营', '工具服务订阅'),
    # ---- 非消费/对冲（保留旧桶） ----
    '退款': ('退款/对冲', '退款冲减'),
    '退款/冲销': ('退款/对冲', '退款冲减'),
    '资金过卡(排除)': ('资金过卡', '过卡资金'),
    '内部转账(排除)': ('亲情往来(非消费)', '家庭内部转账'),
    '利息(排除)': ('资金过卡', '利息'),
    '保险理赔收入(排除)': ('资金过卡', '保险理赔'),
    '伙食费收入(搭伙同事)-冲抵': ('资金过卡', '搭伙同事伙食费冲抵'),
    '家人代存(妈妈)-not-expense': ('亲情往来(非消费)', '家人代存'),
    '家人代存/内部-排除': ('亲情往来(非消费)', '家人代存'),
    '已退回转账(搭伙同事)-排除': ('亲情往来(非消费)', '已退回转账'),
    '信用卡账单周期汇总(9月)': ('信用卡账单聚合', '账单周期汇总'),
}

# ============ 后置规则：按 counter/note 精细分流（覆盖 CAT_MAP 默认）============
def refine(row_idx, date, owner, acct, counter, oldcat, note):
    c = str(counter)
    n = str(note)
    # 1. 小区 → 居住-物业费/停车费
    if '小区花园(示例)' in c:
        return ('居住', '物业费(小区)') if '停车场' not in c else ('居住', '停车费')
    if '停车场' in c or '速停车' in c or '停车' in c:
        return ('居住', '停车费')
    # 2. 生活缴费
    if any(k in c for k in ['电力', '燃气', '水费', '生活缴费', '国网']):
        return ('居住', '水电燃气')
    if '中国电信' in c:
        return ('交通通信', '电信通讯')
    # 3. 创业开销归集（阿里云/Cursor/K3/GLM/模型代购人=大模型会员）
    if '阿里云' in c:
        return ('创业经营', '云计算(阿里云)')
    if 'Anysphere' in c or 'CURSOR' in n.upper() or 'Cursor' in c:
        return ('创业经营', 'AI工具(Cursor)')
    if re.search(r'GLM|智谱|bigmodel|ZHIPU', c + n, re.I):
        return ('创业经营', '大模型会员(GLM)')
    if '模型代购人' in c or 'ZHOU WEN' in c.upper():
        return ('创业经营', '大模型会员(GLM·模型代购人)')
    if '金米' in c or '企业微信' in c or '企业服务' in c:
        return ('创业经营', '财税/企业服务')
    if 'K3' in c.upper() or '金蝶' in c:
        return ('创业经营', '软件(K3/金蝶)')
    # 4. 12306/中铁 → 交通通信；4月下旬回老家办婚礼那批 → 加婚礼事件标签（主类仍是交通）
    #    （事件标签在后面统一打）
    # 5. 医疗机构
    if any(k in c for k in ['妇幼保健院', '妇儿中心', '妇儿保健']):
        return ('医疗保健', '宝宝医疗')
    if 'XX医院' in c or '住院' in c or '预交金' in c:
        return ('医疗保健', '配偶手术(待报销)')
    if any(k in c for k in ['一家依', '中味餐饮', '12点宾馆']):
        return ('医疗保健', '陪护(配偶手术)')
    if '佛山' in c and '医院' in c:
        return ('医疗保健', '父亲医疗')
    if '产后康复师' in c:
        return ('医疗保健', '产后康复')
    if '心理咨询机构' in c or '心理咨询' in c:
        return ('医疗保健', '心理咨询')
    if '育婴服务商' in c:
        return ('医疗保健', '母婴护理')
    if 'MAMAHAHA' in c or '早教' in c:
        return ('教育文化娱乐', '宝宝早教')
    # 6. 12306
    if '12306' in c or '中铁' in c or '铁路' in c:
        return ('交通通信', '铁路出行')
    # 7. 大额旅游包团
    if '旅行社' in c:
        return ('孝亲馈赠', '岳父母旅游')
    # 8. 家人转账
    if '父亲' in c: return ('孝亲馈赠', '父亲(买菜/医疗)')
    if '岳父' in c: return ('孝亲馈赠', '岳父')
    if '岳母' in c: return ('孝亲馈赠', '岳母')
    if '母亲' in c:
        # 4/28 一万 = 妈妈垫付婚宴（v7计入）；5/4 两万 = 代存（排除）
        return ('婚礼专项', '婚宴酒席(妈妈经手)') if str(date)[:10] == '2026-04-28' else ('亲情往来(非消费)', '妈妈(代存/婚宴)')
    if '婚宴商户' in c: return ('婚礼专项', '婚宴酒席')
    if '礼品商' in c or '蟹王' in c: return ('孝亲馈赠', '节礼(蟹券)')
    if '阿姨A' in c or '育儿嫂B' in c or '育儿嫂C' in c:
        return ('家庭服务(育儿嫂)', '阿姨/育儿嫂工资')
    if '办公房租商' in c: return ('创业经营', '办公房租')
    if '创业合作方' in c: return ('创业经营', '创业往来(创业合作方)')
    if '搭伙同事' in c: return ('亲情往来(非消费)', '搭伙往来(搭伙同事)')
    return None

# ============ 事件标签 ============
def event_of(date, cat1, cat2, counter, oldcat):
    ev = []
    d = str(date)[:10]
    # 婚礼：4月中下旬-5月的婚礼相关项
    if cat1 in ('婚礼专项',): ev.append('婚礼')
    elif '2026-04-15' <= d <= '2026-05-10' and (cat2 == '铁路出行'):
        ev.append('婚礼')  # 回老家办婚礼的高铁
    elif cat1 == '医疗保健' and cat2 in ('配偶手术(待报销)', '陪护(配偶手术)', '产后康复', '心理咨询') :
        ev.append('配偶手术及康复')
    elif cat1 == '孝亲馈赠' and cat2 == '岳父母旅游':
        ev.append('旅游')
    if 'Deel' in str(counter) or '58136' in str(counter): ev.append('Deel离职')
    return ev

# ============ 补录：房贷（8316→工行MORTGAGE_ACCT_NO）============
MORTGAGE = [
    # (date, amount, note)  从8316流水中核实
    ("2026-04-03", MORTGAGE_MONTHLY, "8316→MORTGAGE_ACCT 月供"),
    ("2026-04-29", MORTGAGE_MONTHLY, "8316→MORTGAGE_ACCT 月供"),
    ("2026-05-21", MORTGAGE_MONTHLY, "8316→MORTGAGE_ACCT 月供"),
    ("2026-07-01", 5000, "8316→MORTGAGE_ACCT 补缴?"),
    ("2026-07-20", MORTGAGE_MONTHLY, "8316→MORTGAGE_ACCT 月供"),
    ("2026-08-20", MORTGAGE_MONTHLY, "8316→MORTGAGE_ACCT 月供"),
    ("2026-09-20", MORTGAGE_MONTHLY, "8316→MORTGAGE_ACCT 月供"),
]

# ============ 计入口径（与 v7 SUMIFS 对齐 + 房贷新增）============
# 排除：仅"亲情往来(非消费)"里的家人代存/内部转账/已退回（爱心公益/搭伙同事冲抵收入 已改回计入）
# 信用卡账单聚合行保留计入（v7 防漏双计设计）；搭伙同事冲抵为收入冲抵（正数入亲情往来但计入净额→需特殊处理）
COUNTED_EXCLUDE_CATS = {'家人代存(妈妈)-not-expense', '家人代存/内部-排除', '已退回转账(搭伙同事)-排除'}

# ============ 主流程 ============
records = []
for i, r in enumerate(data):
    if len(r) < 7: continue
    ym, date, owner, acct, counter, cat, amt = r[0], r[1], r[2], r[3], r[4], r[5], float(r[6])
    note = r[9] if len(r) > 9 else ''
    src = r[8] if len(r) > 8 else ''
    # 新分类
    if cat in CAT_MAP:
        cat1, cat2 = CAT_MAP[cat]
    else:
        cat1, cat2 = '其他用品及服务', '综合消费(未细分)'
    rf = refine(i, date, owner, acct, counter, cat, note)
    if rf: cat1, cat2 = rf
    # 事件标签
    ev = event_of(date, cat1, cat2, counter, cat)
    records.append({
        'ym': ym, 'date': date if len(str(date)) <= 10 else str(date)[:10],
        'owner': owner, 'acct': acct, 'counter': counter, 'cat': cat,
        'cat1': cat1, 'cat2': cat2, 'event': ev,
        'amt': amt, 'src': src, 'note': note
    })

# 房贷补录
for d, a, note in MORTGAGE:
    ym = f"{d[:4]}年{int(d[5:7])}月"
    records.append({
        'ym': ym, 'date': d, 'owner': '暖', 'acct': '招商银行借记卡-8316(暖)',
        'counter': '工商银行-MORTGAGE_TAIL093(房贷还款户)', 'cat': '房贷月供(v8补录)',
        'cat1': '房贷月供', 'cat2': '房贷月供(工行)', 'event': [],
        'amt': float(a), 'src': '配偶招行流水', 'note': note + ' 原被"家庭内部转账"排除，v8补录'
    })

records.sort(key=lambda x: (str(x['date'])[:10], -abs(x['amt'])))

# ============ 对冲配对：负退款行 ↔ 同月或次月同counter正消费行 ============
# 策略：对每个负数行（cat1=退款/对冲），在全部行中找 counter相近 且 amt≈|负数| 的正数行；
# 找不到 counter 相同就找同金额的。配上的两条都打 pairId，前端显示删除线。
pair_id = 0
consumed = set()
negs = [i for i, r in enumerate(records) if r['amt'] < 0 and r['cat1'] in ('退款/对冲', '资金过卡')]
for ni in negs:
    nr = records[ni]
    target = round(-nr['amt'], 2)
    best = None
    # 第一轮：同counter 且金额完全匹配
    for pi, pr in enumerate(records):
        if pi in consumed or pi == ni or pr['amt'] <= 0: continue
        if round(pr['amt'], 2) == target and (pr['counter'] == nr['counter'] or
                                              (nr['counter'] and nr['counter'] in pr['counter']) or
                                              (pr['counter'] and pr['counter'] in nr['counter'])):
            best = pi; break
    # 第二轮：金额匹配(±2元) + counter首2字符匹配
    if best is None:
        for pi, pr in enumerate(records):
            if pi in consumed or pi == ni or pr['amt'] <= 0: continue
            if abs(pr['amt'] - target) <= 2 and pr['counter'][:2] and pr['counter'][:2] == nr['counter'][:2]:
                best = pi; break
    if best is not None:
        pair_id += 1
        records[ni]['pairId'] = pair_id
        records[best]['pairId'] = pair_id
        consumed.add(best)

json.dump(records, open(f"{BASE}/_v8_rows.json", 'w'), ensure_ascii=False, indent=1)

# ============ 汇总 ============
from collections import Counter
print("总行数:", len(records))
print("\n=== cat1 分布 ===")
c1 = defaultdict(lambda: [0, 0.0])
for r in records: c1[r['cat1']][0] += 1; c1[r['cat1']][1] += r['amt']
for k, (n, s) in sorted(c1.items(), key=lambda x: -x[1][1]):
    print(f"  {k}: {n}笔 {s:,.2f}")
print("\n=== 事件标签分布 ===")
ev = Counter(e for r in records for e in r['event'])
print(dict(ev))
print("\n=== 对冲配对 ===")
paired = [r for r in records if 'pairId' in r]
print(f"配对 {pair_id} 对 / {len(paired)} 行")
unpaired_negs = [r for r in records if r['amt'] < 0 and r['cat1'] in ('退款/对冲', '资金过卡') and 'pairId' not in r]
print(f"未配对负数行 {len(unpaired_negs)} 条:")
for r in unpaired_negs[:10]:
    print(f"  {r['date']} {r['counter'][:16]} {r['amt']:,.2f}")
# 净额校验（对齐SUMIFS口径：排除3类家人代存/退回；账单聚合与搭伙同事冲抵计入）
net = sum(r['amt'] for r in records if r['cat'] not in COUNTED_EXCLUDE_CATS)
print(f"\nv8净额(含房贷补录): {net:,.2f}")
print(f"对比v7口径 N → 差异应恰为 房贷77,000")
