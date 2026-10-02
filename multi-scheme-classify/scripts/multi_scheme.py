# -*- coding: utf-8 -*-
"""v9.1 多分类法引擎（修正版）
三分类法每笔同挂：GB统计局八大类 / QS记账软件风格 / ZFB支付宝风格
关键改进：
  1. 统一 keyword 细分池（先于"其他"兜底），GB 也能细分餐饮/网购/打车/订阅
  2. GB 规则：网购/外卖→食品烟酒或生活用品，按商户性质
  3. ZFB "其他" 大幅消化（零钱汇总→生活日用·零钱渠道）
"""
import json, re
from collections import defaultdict

BASE = "<工作区目录>"
v8 = json.load(open(f"{BASE}/_v8_rows.json"))

# ============ 统一商户关键词池（三分类法共享，返回 tag） ============
KW = [
    # tag, keywords(counter+note 匹配)
    ('外卖餐饮', ['美团', '饿了吗', '饿了么', '蜜雪冰城', '餐饮', '面馆', '餐厅', 'Restaurant', 'CATER', '金炉', '糖水铺', '鱼汤', '美食店', 'NCC', '一记面馆', 'LIUSHUN', 'FEIZAI', 'JINGUANGGE']),
    ('商超买菜', ['山姆', '沃尔玛', '百果园', '盒马', '叮咚', '朴朴', '百草味', '钱大妈']),
    ('网购平台', ['淘宝', '京东', '拼多多', '唯品会', '得物', 'TAOBAO MERCHANT', '百亿', '天猫']),
    ('出行打车', ['高德', '滴滴', '哈啰', '顺风车', '出租', '12306', '中铁', '铁路', '机票', '航旅', 'HELLOBIKE', 'HELLO BIKE', '一喂', '嘀嗒']),
    ('数字订阅', ['App Store', 'Apple Music', '哔哩哔哩', '知乎', '起点', '爱奇艺', '腾讯视频', '优酷', '网易云音乐', 'QQ音乐', '订阅', 'Cursor', 'WPS', 'iCloud', '云存储', ' Valve', 'Steam', '暂停实验室']),
    ('医疗健康', ['医院', '药房', '药店', '好大夫', '中医', '中医院', '肿瘤', '妇幼保健院']),
    ('快递物流', ['菜鸟', '顺丰', '快递', '物流', '京东物流']),
    ('转账小额', ['微信转账', '群接龙', '银联商户', '银联  微信转账']),
    ('生活服务', ['顺易通', '美团单车', '哈啰单车']),
]

def kw_tag(r):
    s = str(r['counter']) + str(r.get('note', ''))
    for tag, keys in KW:
        for k in keys:
            if k in s:
                return tag
    return None

# 零钱渠道
def is_zb(r):
    return r.get('cat') == '日常消费(零钱渠道汇总)' or r.get('cat') == '日常消费(配偶零钱汇总)' or '零钱' in str(r['counter'])

def to_gb(r):
    """统计局八大类（细分版）"""
    c1, c2, tag = r['cat1'], r['cat2'], kw_tag(r)
    if c1 not in ('其他用品及服务',):
        return (c1, c2)
    # 细分池
    if is_zb(r): return ('其他用品及服务', '零钱渠道汇总')
    if tag == '外卖餐饮': return ('食品烟酒', '餐饮外卖')
    if tag == '商超买菜': return ('食品烟酒', '商超买菜')
    if tag == '网购平台': return ('生活用品及服务', '网购日用')
    if tag == '出行打车': return ('交通通信', '打车/共享出行')
    if tag == '数字订阅': return ('教育文化娱乐', '数字订阅')
    if tag == '医疗健康': return ('医疗保健', '门诊药品')
    if tag == '快递物流': return ('生活用品及服务', '快递')
    if tag == '转账小额': return ('其他用品及服务', '转账/小额杂项')
    return ('其他用品及服务', '综合(未细分)')

def to_qs(r):
    """记账软件风格"""
    c1, c2, tag = r['cat1'], r['cat2'], kw_tag(r)
    if c1 == '房贷月供': return ('居家物业', '房贷月供')
    if c1 == '退款/对冲': return ('退款冲销', '退款')
    if c1 == '资金过卡': return ('资金流转', '过卡/利息/理赔')
    if c1 == '亲情往来(非消费)':
        if '公益' in r['cat']: return ('人情往来', '公益捐赠')
        if '搭伙同事' in r['cat']: return ('资金流转', '伙食费冲抵(搭伙同事)')
        return ('人情往来', '家人代存/内部')
    if c1 == '信用卡账单聚合': return ('信用卡账单', '账单汇总')
    if c1 == '医疗保健':
        m = {'配偶手术(待报销)': '配偶手术及康复', '陪护(配偶手术)': '陪护', '产后康复': '产后康复', '心理咨询': '心理咨询', '宝宝医疗': '宝宝医疗', '父亲医疗': '孝亲医疗', '门诊药品': '门诊药品'}
        return ('医疗保险', m.get(c2, '母婴护理'))
    if c1 == '保险保障': return ('金融保险', '保费(社保/商业险)')
    if c1 == '创业经营': return ('创业经营', c2)
    if c1 == '婚礼专项': return ('人情往来', '婚嫁事项')
    if c1 == '孝亲馈赠': return ('人情往来', '孝亲/节礼/旅游')
    if c1 == '家庭服务(育儿嫂)': return ('居家物业', '家庭服务(育儿嫂)')
    if c1 == '食品烟酒': return ('食品酒水', c2 if c2 != '伙食买菜(父亲经手)' else '伙食买菜(父亲)')
    if c1 == '衣着': return ('衣服饰品', c2)
    if c1 == '居住':
        if c2.startswith('物业费'): return ('居家物业', '物业费')
        if c2.startswith('水电'): return ('居家物业', '水电燃气')
        if c2 == '停车费': return ('行车交通', '停车费')
        return ('居家物业', c2)
    if c1 == '生活用品及服务': return ('购物淘宝' if tag in ('网购平台',) else '日常用品', '网购日用' if tag == '网购平台' else c2)
    if c1 == '交通通信':
        if c2 == '电信通讯': return ('交流通讯', '话费网费')
        return ('行车交通', '铁路出行' if '铁路' in c2 else '打车/公交')
    if c1 == '教育文化娱乐': return ('休闲娱乐', c2)
    # 其他用品及服务 → 细分
    if is_zb(r): return ('日常用品', '零钱渠道汇总')
    if tag == '外卖餐饮': return ('食品酒水', '餐饮外卖')
    if tag == '商超买菜': return ('食品酒水', '商超买菜')
    if tag == '网购平台': return ('购物淘宝', '网购综合')
    if tag == '出行打车': return ('行车交通', '打车/火车')
    if tag == '数字订阅': return ('休闲娱乐', '订阅/数字服务')
    if tag == '医疗健康': return ('医疗保险', '门诊药品')
    if tag == '快递物流': return ('日常用品', '快递')
    return ('日常用品', '综合(未细分)')

def to_zfb(r):
    """支付宝风格"""
    c1, c2, tag = r['cat1'], r['cat2'], kw_tag(r)
    if c1 == '房贷月供': return ('生活日用', '房贷月供')
    if c1 == '退款/对冲': return ('退款', '退款')
    if c1 == '资金过卡': return ('转账红包', '过卡/利息/理赔')
    if c1 == '亲情往来(非消费)':
        if '公益' in r['cat']: return ('公益捐赠', '爱心助学')
        if '搭伙同事' in r['cat']: return ('转账红包', '伙食费冲抵(搭伙同事)')
        return ('人情往来', '家人代存/内部')
    if c1 == '信用卡账单聚合': return ('信用卡还款', '账单汇总')
    if c1 == '医疗保健':
        m = {'配偶手术(待报销)': '配偶手术及康复', '陪护(配偶手术)': '陪护', '产后康复': '产后康复', '心理咨询': '心理咨询', '宝宝医疗': '宝宝医疗', '父亲医疗': '孝亲医疗', '门诊药品': '门诊药品'}
        return ('医疗健康', m.get(c2, '母婴护理'))
    if c1 == '保险保障': return ('医疗健康', '保险保障')
    if c1 == '创业经营': return ('创业经营', c2)
    if c1 == '婚礼专项': return ('人情往来', '婚嫁事项')
    if c1 == '孝亲馈赠': return ('人情往来', '孝亲馈赠')
    if c1 == '家庭服务(育儿嫂)': return ('生活日用', '家庭服务(育儿嫂)')
    if c1 == '食品烟酒': return ('餐饮美食', c2 if c2 != '伙食买菜(父亲经手)' else '伙食买菜(父亲)')
    if c1 == '衣着': return ('购物消费', '衣服饰品')
    if c1 == '居住':
        if c2.startswith('物业费'): return ('生活日用', '物业费')
        if c2.startswith('水电'): return ('生活日用', '水电燃气')
        if c2 == '停车费': return ('交通出行', '停车费')
        return ('生活日用', c2)
    if c1 == '生活用品及服务': return ('购物消费', '网购日用' if tag == '网购平台' else '日用百货')
    if c1 == '交通通信':
        if c2 == '电信通讯': return ('生活日用', '话费网费')
        return ('交通出行', '铁路出行' if '铁路' in c2 else '打车/公交')
    if c1 == '教育文化娱乐': return ('教育文化', c2)
    # 其他用品及服务 → 细分
    if is_zb(r): return ('生活日用', '零钱渠道汇总')
    if tag == '外卖餐饮': return ('餐饮美食', '餐饮外卖')
    if tag == '商超买菜': return ('餐饮美食', '商超买菜')
    if tag == '网购平台': return ('购物消费', '网购综合')
    if tag == '出行打车': return ('交通出行', '打车/火车')
    if tag == '数字订阅': return ('娱乐休闲', '订阅/数字服务')
    if tag == '医疗健康': return ('医疗健康', '门诊药品')
    if tag == '快递物流': return ('生活日用', '快递')
    return ('其他', '综合(未细分)')

out = []
for r in v8:
    nr = dict(r)
    g1, g2 = to_gb(r)
    q1, q2 = to_qs(r)
    z1, z2 = to_zfb(r)
    # review 列（腾讯文档手动改写用）：GB主类/GB子类/QS主类/QS子类/ZFB主类/ZFB子类 六列留空
    nr['catGB'] = [g1, g2]
    nr['catQS'] = [q1, q2]
    nr['catZFB'] = [z1, z2]
    nr['review'] = ''
    out.append(nr)

json.dump(out, open(f"{BASE}/_v9_rows.json", 'w'), ensure_ascii=False, indent=1)

# ===== 汇总 =====
print('总行数:', len(out))
for label, key in [('GB统计局', 'catGB'), ('QS记账软件', 'catQS'), ('ZFB支付宝', 'catZFB')]:
    agg = defaultdict(float); n = defaultdict(int)
    for r in out: agg[r[key][0]] += r['amt']; n[r[key][0]] += 1
    print(f'\n=== {label} ===')
    for k, v in sorted(agg.items(), key=lambda x: -x[1]):
        print(f'  {k}: {n[k]}笔 {v:,.0f}')
