# -*- coding: utf-8 -*-
"""生成 demo_data.json（假数据）+ demo 版仪表盘 HTML（GitHub Pages 用）
数据语义修复：
1. 婚嫁报销冲减只出现负数（不再出现正数消费挂这个子类）
2. 房贷月供每月固定 1 笔 6,800（7笔）
3. 补 dedup 演示规则（R01-R05 假数据）+ billMonthly + exclCats
输出：
  expense-dashboard/assets/demo_data.json
  docs/index.html（demo 仪表盘，Chart.js 内嵌，单文件）
"""
import json, random, copy

random.seed(2026)

CATS = {
 '食品烟酒': [('餐饮外卖',0.35),('商超买菜',0.45),('伙食买菜(父亲经手)',0.2)],
 '居住': [('物业费(小区)',0.35),('水电燃气',0.45),('停车费',0.2)],
 '交通通信': [('打车/共享出行',0.4),('铁路出行',0.3),('电信通讯',0.3)],
 '心理健康': [('心理咨询',1.0)],
 '家庭服务(育儿嫂)': [('阿姨/育儿嫂工资',1.0)],
 '房贷月供': [('房贷月供(示例银行)',1.0)],
 '医疗保健': [('宝宝医疗',0.4),('门诊药品',0.4),('配偶手术(待报销)',0.2)],
 '婴儿用品': [('用品(奶粉/尿布/玩具/衣)',1.0)],
 '教育文化娱乐': [('数字订阅',0.6),('宝宝早教',0.4)],
 '生活用品及服务': [('网购日用',0.7),('快递',0.3)],
 '孝亲馈赠': [('岳父母旅游',0.5),('节礼',0.5)],
 '婚礼专项': [('婚宴酒席',1.0)],
 '创业经营': [('云计算',0.4),('大模型会员',0.4),('办公房租',0.2)],
 '其他用品及服务': [('零钱渠道逐笔',0.6),('综合(未细分)',0.4)],
}
SHOPS = {
 '餐饮外卖':['示例外卖·饺子馆','示例餐厅·茶点铺'],
 '商超买菜':['示例超市·龙华店','示例生鲜·果园站'],
 '伙食买菜(父亲经手)':['父亲·买菜钱'],
 '物业费(小区)':['示例物业·幸福里'],
 '水电燃气':['示例电力公司','示例燃气公司'],
 '停车费':['示例停车场·月租'],
 '打车/共享出行':['示例出行·快车'],
 '铁路出行':['示例铁路12306'],
 '电信通讯':['示例移动通信'],
 '心理咨询':['示例心理咨询中心'],
 '阿姨/育儿嫂工资':['阿姨·示例','育儿嫂·示例'],
 '房贷月供(示例银行)':['房贷扣款·示例银行'],
 '宝宝医疗':['示例儿童医院'],
 '门诊药品':['示例大药房'],
 '配偶手术(待报销)':['示例医院·住院'],
 '用品(奶粉/尿布/玩具/衣)':['示例母婴店'],
 '数字订阅':['示例视频会员','示例云盘'],
 '宝宝早教':['示例早教中心'],
 '网购日用':['示例商城'],
 '快递':['示例快递'],
 '岳父母旅游':['示例旅行社'],
 '节礼':['节礼·示例'],
 '婚宴酒席':['示例酒店·宴会厅'],
 '云计算':['示例云服务商'],
 '大模型会员':['示例大模型·会员'],
 '办公房租':['示例产业园·房租'],
 '零钱渠道逐笔':['示例小商户'],
 '综合(未细分)':['示例综合商户'],
}
def qs(c1, c2):
    m = {'食品烟酒':'食品酒水','居住':'居家物业','交通通信':'行车交通','心理健康':'心理健康',
         '家庭服务(育儿嫂)':'居家物业','房贷月供':'居家物业','医疗保健':'医疗保险','婴儿用品':'日常用品',
         '教育文化娱乐':'休闲娱乐','生活用品及服务':'购物淘宝','孝亲馈赠':'人情往来','婚礼专项':'人情往来',
         '创业经营':'创业经营','其他用品及服务':'日常用品'}
    return [m.get(c1,'日常用品'), c2]
def zfb(c1, c2):
    m = {'食品烟酒':'餐饮美食','居住':'生活日用','交通通信':'交通出行','心理健康':'心理健康',
         '家庭服务(育儿嫂)':'生活日用','房贷月供':'生活日用','医疗保健':'医疗健康','婴儿用品':'购物消费',
         '教育文化娱乐':'教育文化','生活用品及服务':'购物消费','孝亲馈赠':'人情往来','婚礼专项':'人情往来',
         '创业经营':'创业经营','其他用品及服务':'其他'}
    return [m.get(c1,'其他'), c2]

records = []
# 固定支出：房贷每月1笔 + 育儿嫂每月1笔 + 心理咨询每月1-2笔
for m in range(3, 10):
    ym = f'2026年{m}月'
    # 房贷
    records.append({'ym':ym,'date':f'2026-{m:02d}-20','owner':'配偶','acct':'示例储蓄卡',
        'counter':'房贷扣款·示例银行','cat':'房贷月供','cat1':'房贷月供','cat2':'房贷月供(示例银行)',
        'catGB':['房贷月供','房贷月供(示例银行)'],'catQS':qs('房贷月供','房贷月供(示例银行)'),
        'catZFB':zfb('房贷月供','房贷月供(示例银行)'),'event':[],'amt':6800.0,'src':'示例银行流水','note':'demo','review':''})
    # 育儿嫂
    records.append({'ym':ym,'date':f'2026-{m:02d}-05','owner':'本人','acct':'示例储蓄卡',
        'counter':'阿姨·示例','cat':'育儿嫂工资','cat1':'家庭服务(育儿嫂)','cat2':'阿姨/育儿嫂工资',
        'catGB':['家庭服务(育儿嫂)','阿姨/育儿嫂工资'],'catQS':qs('家庭服务(育儿嫂)','阿姨/育儿嫂工资'),
        'catZFB':zfb('家庭服务(育儿嫂)','阿姨/育儿嫂工资'),'event':[],'amt':7500.0,'src':'示例银行流水','note':'demo','review':''})
    # 心理咨询
    for _ in range(random.randint(1,2)):
        records.append({'ym':ym,'date':f'2026-{m:02d}-{random.randint(1,28):02d}','owner':'配偶','acct':'示例信用卡',
            'counter':'示例心理咨询中心','cat':'心理咨询','cat1':'心理健康','cat2':'心理咨询',
            'catGB':['心理健康','心理咨询'],'catQS':qs('心理健康','心理咨询'),
            'catZFB':zfb('心理健康','心理咨询'),'event':[],'amt':random.choice([1880.0,2350.0,2820.0]),
            'src':'示例账单','note':'demo','review':''})
# 4月婚礼：酒席大额 + 高铁(婚礼事件) + 5月父亲报销冲减
wed_items = [
 ('2026-04-26','示例酒店·宴会厅','婚宴酒席',38800.0),
 ('2026-04-26','示例铁路12306','铁路出行',3060.0),
 ('2026-04-27','示例铁路12306','铁路出行',605.0),
]
for d, shop, c2, amt in wed_items:
    m = int(d[5:7])
    records.append({'ym':f'2026年{m}月','date':d,'owner':'本人','acct':'示例信用卡','counter':shop,
        'cat':'婚礼'+c2,'cat1':'婚礼专项' if c2=='婚宴酒席' else '交通通信','cat2':c2,
        'catGB':['婚礼专项' if c2=='婚宴酒席' else '交通通信', c2],
        'catQS':qs('婚礼专项' if c2=='婚宴酒席' else '交通通信',c2),
        'catZFB':zfb('婚礼专项' if c2=='婚宴酒席' else '交通通信',c2),
        'event':['婚礼'],'amt':amt,'src':'示例账单','note':'demo 婚礼事件','review':''})
records.append({'ym':'2026年5月','date':'2026-05-08','owner':'本人','acct':'示例储蓄卡',
    'counter':'父亲·婚礼报销','cat':'婚礼报销','cat1':'婚礼专项','cat2':'婚嫁报销冲减',
    'catGB':['婚礼专项','婚嫁报销冲减'],'catQS':['人情往来','婚嫁报销'],
    'catZFB':['人情往来','婚嫁报销'],'event':['婚礼'],'amt':-20000.0,'src':'示例银行流水','note':'demo 报销冲减','review':''})
# 日常消费
for m in range(3, 10):
    for _ in range(random.randint(42, 62)):
        c1 = random.choices(list(CATS), weights=[10,6,6,0,0,0,4,3,3,6,2,0,2,12])[0]  # 固定项已单列
        c2 = random.choices([x[0] for x in CATS[c1]], weights=[x[1] for x in CATS[c1]])[0]
        amt = round(random.choice([random.uniform(8,120), random.uniform(120,900), random.uniform(900,6000)]), 2)
        d = f'2026-{m:02d}-{random.randint(1,28):02d}'
        records.append({'ym':f'2026年{m}月','date':d,'owner':random.choice(['本人','配偶']),
            'acct':random.choice(['示例信用卡','示例储蓄卡','示例支付渠道']),
            'counter':random.choice(SHOPS[c2]),'cat':'示例消费','cat1':c1,'cat2':c2,
            'catGB':[c1,c2],'catQS':qs(c1,c2),'catZFB':zfb(c1,c2),'event':[],
            'amt':amt,'src':'示例数据','note':'demo','review':''})
records.sort(key=lambda x: (x['date'], -abs(x['amt'])))

# ===== 对账台账（demo 8 组）=====
recon = [
 {'gid':'D001','type':'退款冲销','left':{'date':'2026-04-02','counter':'示例商城','amt':-89.0,'acct':'示例信用卡'},
  'right':{'date':'2026-04-01','counter':'示例商城','amt':89.0,'acct':'示例信用卡'},'note':'退款↔原消费'},
 {'gid':'D002','type':'退款冲销','left':{'date':'2026-06-18','counter':'示例母婴店','amt':-129.0,'acct':'示例支付渠道'},
  'right':{'date':'2026-06-17','counter':'示例母婴店','amt':129.0,'acct':'示例支付渠道'},'note':'退货退款'},
 {'gid':'D003','type':'信用卡还款','left':{'date':'2026-05-10','counter':'信用卡自动还款','amt':-3200.0,'acct':'示例储蓄卡'},
  'right':{'date':'2026-05-10','counter':'信用卡入账','amt':3200.0,'acct':'示例信用卡'},'note':'储蓄卡↔信用卡'},
 {'gid':'D004','type':'信用卡还款','left':{'date':'2026-06-10','counter':'信用卡自动还款','amt':-4100.0,'acct':'示例储蓄卡'},
  'right':{'date':'2026-06-10','counter':'信用卡入账','amt':4100.0,'acct':'示例信用卡'},'note':'储蓄卡↔信用卡'},
 {'gid':'D005','type':'渠道双记','left':{'date':'2026-07-15','counter':'示例出行·快车','amt':-23.5,'acct':'示例支付渠道'},
  'right':{'date':'2026-07-15','counter':'渠道扣款','amt':23.5,'acct':'示例信用卡'},'note':'渠道流水↔银行扣费(银行侧免记)'},
 {'gid':'D006','type':'渠道双记','left':{'date':'2026-08-02','counter':'示例商城','amt':-156.8,'acct':'示例支付渠道'},
  'right':{'date':'2026-08-02','counter':'渠道扣款','amt':156.8,'acct':'示例信用卡'},'note':'渠道流水↔银行扣费(银行侧免记)'},
 {'gid':'D007','type':'转账退回','left':{'date':'2026-05-20','counter':'朋友·退回','amt':-500.0,'acct':'示例支付渠道'},
  'right':{'date':'2026-05-19','counter':'朋友·转入','amt':500.0,'acct':'示例支付渠道'},'note':'转出被退回'},
 {'gid':'D008','type':'资金过卡','left':{'date':'2026-09-01','counter':'保证金退回','amt':-8000.0,'acct':'示例储蓄卡'},
  'right':{'date6':'','date':'2026-08-25','counter':'保证金缴纳','amt':8000.0,'acct':'示例储蓄卡'},'note':'资金过卡(非消费)'},
]
# 清理笔误字段
for g in recon:
    g['left'] = {k:v for k,v in g['left'].items() if not k.endswith('6')}
    g['right'] = {k:v for k,v in g['right'].items() if not k.endswith('6')}

demo = {
 'records': records,
 'recon': recon,
 'billMonthly': {f'{m}月': {'本人': round(random.uniform(3000,9000),2), '配偶': round(random.uniform(2000,7000),2)} for m in range(3,10)},
 'dedup': {'visible': [], 'invisible': [
   {'id':'R01','title':'示例渠道A与银行卡同源(全跳过)','why':'同一张卡的两种导出','n':6,'impact':2300.0,'items':[
      {'date':'2026-05-02','counter':'示例商城','amt':156.8,'note':'渠道与银行双记'}]},
   {'id':'R02','title':'信用卡账单周期防重窗口','why':'账单已整期计入,渠道侧跳过','n':4,'impact':780.5,'items':[
      {'date':'2026-08-20','counter':'示例视频会员','amt':30.0,'note':'窗口内渠道笔'}]},
   {'id':'R03','title':'全额退款整笔跳过','why':'状态=已全额退款','n':2,'impact':230.0,'items':[
      {'date':'2026-06-18','counter':'示例母婴店','amt':129.0,'note':'已全额退款'}]},
 ]},
 'exclCats': ['家人代存(示例)-not-expense', '内部转账(示例)-排除'],
 'sheetUrl': 'https://docs.qq.com/sheet/YOUR_FILE_ID',
}

import os
os.makedirs('expense-dashboard/assets', exist_ok=True)
json.dump(demo, open('expense-dashboard/assets/demo_data.json','w'), ensure_ascii=False, indent=1)

net = sum(r['amt'] for r in records)
print(f'demo records: {len(records)} 条 | 净额 {net:,.2f}')
from collections import Counter
for k, v in Counter(r['cat1'] for r in records).most_common():
    print(f'  {k}: {v}笔 {sum(r["amt"] for r in records if r["cat1"]==k):,.0f}')
