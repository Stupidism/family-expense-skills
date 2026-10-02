# -*- coding: utf-8 -*-
"""仪表盘 v10 大重构：
顺序：①六个数字 → ②三分类法横排对比(主类饼图+子类排行，可切柱状) → ③按月分布(折线，可切柱状)+按日分布
     → ④月度趋势分组明细(前移) → ⑤对账视图(左右对称) → ⑥明细检索(平铺过滤，先选分类标准)
每条明细带链接跳转腾讯表格对应格子（url #sheetId!A{row} 格式）
图表：纯 SVG 实现（饼图/折线图/柱状图），无外部依赖"""
import json

BASE = '<工作区目录>'
records = json.load(open(f'{BASE}/_v10_rows.json'))
recon = json.load(open(f'{BASE}/_v10_recon.json'))
dedup = json.load(open(f'{BASE}/_dedup_audit.json'))
bills = json.load(open(f'{BASE}/_eml_bills_parsed.json'))

for rule in dedup['invisible']:
    if rule['id'] == 'R05':
        rule['flag'] = '1298九月账单：表内明细vs账单应还650.54待核（见"信用卡月账单汇总验算"表）'

bill_monthly = {}
for k, b in bills.items():
    if b['year'] != '2026' or not (3 <= b['month'] <= 9): continue
    mk = f"{b['month']}月"
    bill_monthly.setdefault(mk, {}).setdefault(b['who'], 0)
    bill_monthly[mk][b['who']] += round(sum(t['amt'] for t in b['txns']), 2)

V7_EXCL = ['家人代存(妈妈)-not-expense', '家人代存/内部-排除', '已退回转账(搭伙同事)-排除']
SHEET_URL = 'https://docs.qq.com/sheet/YOUR_DOC_URL_TOKEN'
DETAIL_SHEET = 'SHEET_6TgC25'

# 行号映射（明细表第2行起，第i条=index+2）
for i, r in enumerate(records):
    r['sheetRow'] = i + 2
    r['sheetLink'] = f"{SHEET_URL}?_fid=YOUR_FILE_ID&tab={DETAIL_SHEET}&x=0&y={i+1}"
    # 备注：若浏览器不定位，打开后 Ctrl+G 输入 A{row} 跳转

payload = json.dumps({'records': records, 'recon': recon, 'billMonthly': bill_monthly,
                      'dedup': {'visible': dedup['visible'], 'invisible': dedup['invisible']},
                      'exclCats': V7_EXCL, 'sheetUrl': SHEET_URL}, ensure_ascii=False)

CHARTJS = open('<工作区目录>').read() if __import__('os').path.exists('/tmp/chart.umd.min.js') else ''
page = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>家庭开销分析仪表盘</title>
<style>
:root{--bg:#f7f8fa;--card:#fff;--ink:#1a2233;--sub:#68738a;--line:#e6e9f0;--red:#d5443a;--blue:#3a6fd5;--gold:#b98a2f;--green:#2e8b57}
*{box-sizing:border;margin:0;padding:0}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);padding:24px}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--sub);font-size:13px;margin-bottom:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .t{font-size:12px;color:var(--sub)}
.kpi .v{font-size:24px;font-weight:700;margin-top:4px}
.kpi .d{font-size:11px;color:var(--sub);margin-top:2px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:18px}
.panel h2{font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.tri{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:1100px){.tri{grid-template-columns:1fr}}
.scheme-col{border:1px solid var(--line);border-radius:10px;padding:12px;background:#fcfdfe}
.scheme-col h3{font-size:13px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}
.viewtoggle{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:11px}
.viewtoggle span{padding:3px 10px;cursor:pointer;background:#fff;color:var(--sub)}
.viewtoggle span.on{background:var(--ink);color:#fff}
.pie-wrap{display:flex;gap:10px;align-items:center;justify-content:center;padding:6px 0 10px}
.pie-legend{font-size:11px;line-height:1.7;flex:1;min-width:120px}
.pie-legend .sw{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:middle}
.bar-row{display:flex;align-items:center;gap:8px;margin-bottom:5px;cursor:pointer}
.bar-label{width:110px;font-size:11.5px;text-align:right;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{flex:1;background:#eef0f4;border-radius:5px;height:18px}
.bar-fill{height:100%;border-radius:5px;min-width:2px}
.bar-val{width:86px;font-size:11px;flex-shrink:0}
.filters{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:12px;align-items:center}
.chip{padding:4px 12px;border-radius:16px;border:1px solid var(--line);background:#fff;font-size:12.5px;cursor:pointer;user-select:none}
.chip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.chip.warn{color:var(--gold);border-color:var(--gold)}
.flatbar{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.flatbar .chip{font-size:12px;padding:4px 11px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{position:sticky;top:0;background:#fafbfc;text-align:left;padding:8px;border-bottom:2px solid var(--line);font-weight:600;cursor:pointer;white-space:nowrap;z-index:2}
td{padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
tr:hover td{background:#f4f7ff}
.amt-neg{color:var(--green)}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;background:#eef1f6;color:#4a5570;margin-right:3px}
.tag.ev{background:#37474f;color:#fff}
.note{color:var(--sub);font-size:11px}
#tbl-wrap{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:8px}
a.tlink{color:var(--blue);text-decoration:none;font-size:11px;white-space:nowrap}
a.tlink:hover{text-decoration:underline}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:900px){.two-col{grid-template-columns:1fr}}
.warn-box{background:#fff8e6;border:1px solid #f0d998;border-radius:8px;padding:10px 14px;font-size:12.5px;margin-bottom:14px}
.mini{font-size:11px;color:var(--sub)}
.monthgrp{border:1px solid var(--line);border-radius:10px;margin-bottom:12px;overflow:hidden}
.mg-head{display:flex;align-items:center;gap:12px;padding:10px 15px;background:linear-gradient(90deg,#f4f7f4,#fafbfc);cursor:pointer}
.mg-head .m{font-size:14px;font-weight:700;min-width:70px}
.mg-head .net{font-size:14px;font-weight:700;color:var(--red)}
.mg-head .mom{font-size:11px;padding:2px 8px;border-radius:10px;background:#eef1f6;color:#4a5570}
.mg-head .n{font-size:11px;color:var(--sub)}
.mg-head .spark{flex:1;height:12px;background:#eef0f4;border-radius:6px;overflow:hidden;min-width:50px}
.mg-head .spark div{height:100%;background:linear-gradient(90deg,#2e8b57,#d5443a)}
.mg-body{display:none}
.monthgrp.open .mg-body{display:block}
.mg-tbl-wrap{max-height:400px;overflow:auto}
.mrow-total{background:#f6f8f6;font-weight:700}
tr.paired td{color:#98a2b8}
.strike{text-decoration:line-through;color:#98a2b8}
.pairsig{display:inline-block;font-size:10px;color:#98a2b8;margin-left:4px}
/* 对账视图：左右分栏双列手风琴 */
#reconView{display:grid;grid-template-columns:1fr 1fr;gap:10px;max-height:560px;overflow-y:auto;padding-right:4px}
@media(max-width:1100px){#reconView{grid-template-columns:1fr}}
.recon-grp{border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff}
.recon-head{display:flex;gap:8px;align-items:center;padding:8px 12px;background:#fafbfd;cursor:pointer;font-size:12px}
.recon-head .gid{font-weight:700;color:var(--sub);font-size:10px;background:#eef1f6;border-radius:5px;padding:1px 6px}
.recon-body{display:none;border-top:1px solid var(--line);background:#fcfdff;padding:4px 0}
.recon-grp.open .recon-body{display:block}
.recon-pair{display:grid;grid-template-columns:1fr 44px 1fr;font-size:11.5px;border-bottom:1px dashed #eef0f4}
.recon-pair:last-child{border-bottom:none}
.recon-cell{padding:6px 10px;min-width:0}
.recon-cell.L{text-align:right;border-right:1px dashed var(--line)}
.recon-cell.R{border-left:1px dashed var(--line)}
.recon-arrow{display:flex;align-items:center;justify-content:center;color:var(--sub)}
.recon-amt-d{color:var(--red);font-weight:700}
.recon-amt-c{color:var(--green);font-weight:700}
.recon-note{color:var(--sub);font-size:10.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rule{border:1px solid var(--line);border-radius:10px;margin-bottom:8px;overflow:hidden;background:#fff}
.rule-head{display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;user-select:none}
.rule-head .rid{font-size:10px;font-weight:700;color:var(--sub);background:#eef1f6;border-radius:5px;padding:1px 6px;flex-shrink:0}
.rule-head .rtitle{font-size:12.5px;font-weight:600;flex:1}
.rule-head .rstat{font-size:11.5px;font-weight:700;flex-shrink:0}
.rule-body{display:none;border-top:1px solid var(--line);max-height:300px;overflow:auto;background:#fbfcfe}
.rule.open .rule-body{display:block}
.rule.alert{border-color:#f0b4ae;background:#fff9f8}
.flagline{padding:6px 12px;background:#fdeceb;color:var(--red);font-size:11.5px;font-weight:600;border-top:1px solid #f5c9c4}
#vis-filter{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.scheme-pick{display:flex;gap:8px;margin-bottom:12px}
.scheme-pick .chip{font-size:13px;padding:5px 16px;font-weight:600}
</style>
</head>
<body>
<h1>家庭开销分析仪表盘 <span class="mini">（v10 · 2026年3-9月）</span></h1>
<div class="sub">对冲不加减行、只标注（明细表S/T列）｜每条明细可跳转腾讯表格 ｜ 净开销 <b>N</b>（含房贷77,000）</div>

<div class="grid" id="kpis"></div>

<div class="panel">
  <h2>三分类法对比
    <span class="viewtoggle" id="triToggle"><span class="on" onclick="setTriView('pie')">饼图</span><span onclick="setTriView('bar')">柱状</span></span>
  </h2>
  <div class="tri" id="triMain"></div>
  <div class="tri" id="triSub" style="margin-top:10px"></div>
</div>

<div class="two-col">
<div class="panel">
  <h2>按月分布
    <span class="viewtoggle" id="mToggle"><span class="on" onclick="setMView('line')">折线</span><span onclick="setMView('bar')">柱状</span></span>
  </h2>
  <div id="monthView"></div>
  <div class="mini" style="margin-top:6px">信用卡账单口径：<span id="billCmp"></span></div>
</div>
<div class="panel">
  <h2>按日分布
    <span class="viewtoggle" id="dToggle"><span class="on" onclick="setDView('line')">折线</span><span onclick="setDView('dot')">散点</span></span>
  </h2>
  <div class="flatbar" id="dayMonthPick"></div>
  <div id="dayView"></div>
</div>
</div>

<div class="panel">
  <h2>月度趋势 · 分组明细 <span class="mini">（每月内按金额从大到小；点月头展开；分类chips多选，亮的显示/灰的排除）</span></h2>
  <div class="filters">
    <span class="mini">分类标准：</span><span class="chip on" id="mgScGB" onclick="mgSetScheme('GB')">GB</span><span class="chip" id="mgScQS" onclick="mgSetScheme('QS')">QS</span><span class="chip" id="mgScZFB" onclick="mgSetScheme('ZFB')">ZFB</span>
  </div>
  <div class="flatbar" id="mgCatChips"></div>
  <div class="filters">
    <span class="chip" onclick="mgToggleAll(true)">全展开</span>
    <span class="chip" onclick="mgToggleAll(false)">全收起</span>
    <span class="chip on" id="hidePairBtn" onclick="toggleHidePair()">隐藏已对冲行</span>
    <span class="mini" id="mgInfo"></span>
  </div>
  <div id="monthlyView"></div>
</div>

<div class="panel">
  <h2>对账视图 <span class="mini">（左右分栏：出账⇄入账｜类型卡片点击展开｜婚礼报销N已入婚礼专项负项）</span></h2>
  <div class="filters" id="reconFilter"></div>
  <div id="reconView"></div>
  <div class="mini" id="reconSum" style="margin-top:8px"></div>
</div>

<div class="panel">
  <h2>去重源头规则 <span class="mini">（R01-R17，数据写入前被跳过的部分）</span></h2>
  <div id="ruleList"></div>
</div>

<div class="panel">
  <h2>明细检索 <span class="mini">（先选分类标准，再点分类平铺过滤）</span></h2>
  <div class="scheme-pick" id="searchSchemePick"></div>
  <div class="flatbar" id="flatCat1"></div>
  <div class="flatbar" id="flatCat2"></div>
  <div class="flatbar" id="flatEv"></div>
  <div class="flatbar" id="flatMonth"></div>
  <div id="tbl-wrap"><table id="tbl"><thead><tr>
    <th data-k="date">日期</th><th data-k="owner">人</th><th data-k="counter">交易对象</th><th data-k="schemeCat">主类</th><th data-k="schemeCat2">子类</th><th data-k="event">事件</th><th data-k="amt">金额 ⇅</th><th>对冲</th><th>表格</th>
  </tr></thead><tbody></tbody></table></div>
  <div class="mini" style="margin-top:8px">行数：<span id="cnt"></span>｜合计：<span id="sum"></span></div>
</div>

<div class="warn-box" id="todoBox"></div>

<script>__CHARTJS__</script>
<script>
const DATA = __PAYLOAD__;
const recs = DATA.records;
const EXCL = new Set(DATA.exclCats);
const isCounted = r => !EXCL.has(r.cat);
const mainRows = recs.filter(r => !r._hide);   // 对账台账行不在主明细

const SCHEMES = {
  GB:  {name:'GB · 统计局八大类', color:{'食品烟酒':'#c05621','衣着':'#7c3aed','居住':'#2e7d32','生活用品及服务':'#1565c0','交通通信':'#ef6c00','教育文化娱乐':'#c2185b','医疗保健':'#2e8b57','心理健康':'#7b1fa2','其他用品及服务':'#78909c','家庭服务(育儿嫂)':'#558b2f','孝亲馈赠':'#b98a2f','婚礼专项':'#d5443a','创业经营':'#3949ab','房贷月供':'#5d4037','保险保障':'#00695c','退款/对冲':'#9e9e9e','资金过卡':'#9e9e9e','亲情往来(非消费)':'#bdbdbd','信用卡账单聚合':'#90a4ae'}},
  QS:  {name:'QS · 记账软件风格', color:{'食品酒水':'#c05621','衣服饰品':'#7c3aed','居家物业':'#2e7d32','行车交通':'#ef6c00','交流通讯':'#0288d1','休闲娱乐':'#c2185b','人情往来':'#e65100','医疗保险':'#2e8b57','心理健康':'#7b1fa2','金融保险':'#00695c','购物淘宝':'#1565c0','日常用品':'#78909c','创业经营':'#3949ab','退款冲销':'#9e9e9e','资金流转':'#9e9e9e','信用卡账单':'#90a4ae'}},
  ZFB: {name:'ZFB · 支付宝风格', color:{'餐饮美食':'#c05621','购物消费':'#1565c0','交通出行':'#ef6c00','娱乐休闲':'#c2185b','生活日用':'#2e7d32','人情往来':'#e65100','医疗健康':'#2e8b57','心理健康':'#7b1fa2','教育文化':'#6a1b9a','转账红包':'#9e9e9e','退款':'#9e9e9e','信用卡还款':'#90a4ae','公益捐赠':'#43a047','创业经营':'#3949ab','其他':'#78909c'}}
};

let curScheme = 'GB';
let triView = 'pie', mview = 'line';
let flt = {cat1:null, cat2:null, event:null, month:null};
let sortKey = 'amt', sortDir = -1;
let hidePaired = true;
let reconType = '全部';
const mgOpen = {};

const K = (t,v,d)=>`<div class="kpi"><div class="t">${t}</div><div class="v">${v}</div><div class="d">${d}</div></div>`;
function money(n){return n.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})}
const MNUM = m => parseInt((m.match(/(\\d+)月/)||[0,0])[1]);
const months = [...new Set(recs.map(r=>r.ym))].sort((a,b)=>MNUM(a)-MNUM(b));
const events = [...new Set(recs.flatMap(r=>r.event||[]))];
const cat1Of = r => r['cat'+curScheme][0];
const cat2Of = r => r['cat'+curScheme][1];
const cColor = (sk,c) => (SCHEMES[sk].color[c]||'#78909c');

// ===== Chart.js 图表管理 =====
const charts = {};   // id -> Chart 实例
function killChart(id){ if(charts[id]){charts[id].destroy(); delete charts[id];} }
function mkCtx(id, h){ 
  const el = document.getElementById(id);
  if(!el) return null;
  el.innerHTML = `<canvas height="${h||170}"></canvas>`;
  return el.querySelector('canvas').getContext('2d');
}
const TOOLTIP_MONEY = {callbacks:{label:(c)=>` ${c.dataset.label||c.label||''} ${money(typeof c.parsed==='object'?c.parsed.y:c.parsed)}`}};
const FONT = {family:"-apple-system,'PingFang SC','Microsoft YaHei',sans-serif", size:11};

// 饼图（分类法主类分布）
function pieChart(cid, data, colors, h){
  const ctx = mkCtx(cid, h); if(!ctx) return;
  killChart(cid);
  charts[cid] = new Chart(ctx, {
    type: 'doughnut',
    data: {labels: data.map(d=>d[0]), datasets:[{data: data.map(d=>Math.abs(d[1])),
      backgroundColor: data.map(d=>colors[d[0]]||'#999'), borderWidth:1.5, borderColor:'#fff',
      hoverOffset:8}]},
    options: {responsive:true, maintainAspectRatio:false, cutout:'38%',
      plugins:{legend:{display:false},
        tooltip:{...TOOLTIP_MONEY, callbacks:{label:(c)=>{
          const total=c.dataset.data.reduce((s,v)=>s+v,0);
          return ` ${c.label}: ${money(c.parsed)} (${(c.parsed/total*100).toFixed(1)}%)`}}}},
      onClick:(e,els)=>{ if(els.length){const lbl=charts[cid].data.labels[els[0].index]; onPieClick(cid.slice(3), lbl);}}
    }
  });
}
// 折线图（月/日）
function lineChart(cid, labels, vals, color, h, fill){
  const ctx = mkCtx(cid, h); if(!ctx) return;
  killChart(cid);
  charts[cid] = new Chart(ctx, {
    type: 'line',
    data: {labels, datasets:[{data: vals, borderColor:color, backgroundColor:color+'22',
      fill: fill!==false, tension:0.25, pointRadius:4, pointHoverRadius:7,
      pointBackgroundColor:(c)=> vals[c.dataIndex]>=3000 ? '#d5443a' : color,
      pointStyle:'circle'}]},
    options: {responsive:true, maintainAspectRatio:false,
      plugins:{legend:{display:false}, tooltip:TOOLTIP_MONEY},
      scales:{y:{ticks:{color:'#68738a', font:FONT, callback:v=>(v/10000).toFixed(1)+'万'}, grid:{color:'#eef0f4'}},
              x:{ticks:{color:'#68738a', font:FONT, maxRotation:0, autoSkipPadding:8}, grid:{display:false}}},
      onClick:(e,els)=>{ if(els.length){const lbl=labels[els[0].index]; onLineClick(cid, lbl);}}
    }
  });
}
// 散点式柱状（按日·点图，用 bubble 模拟）
function dotChart(cid, labels, vals, color, h){
  const ctx = mkCtx(cid, h); if(!ctx) return;
  killChart(cid);
  const mx = Math.max(...vals, 1);
  charts[cid] = new Chart(ctx, {
    type: 'bubble',
    data: {labels, datasets:[{data: vals.map((v,i)=>({x:i,y:1,r:3+Math.sqrt(v/mx)*14})),
      backgroundColor:(c)=> vals[c.dataIndex]>=3000?'#d5443acc':'#3a6fd5aa',
      borderColor:'transparent'}]},
    options: {responsive:true, maintainAspectRatio:false,
      plugins:{legend:{display:false}, tooltip:{callbacks:{title:(i)=>labels[i[0].dataIndex]+'日', label:(c)=>` 净开销 ${money(vals[c.dataIndex])}`}}},
      scales:{y:{display:false}, x:{ticks:{color:'#68738a', font:FONT, autoSkip:false, callback:(v,i)=>labels[i]}, grid:{display:false}}},
      onClick:(e,els)=>{ if(els.length){onDayDotClick(labels[els[0].index]);}}
    }
  });
}
function render(){
  const counted = recs.filter(isCounted);            // 总额含隐藏负行（对冲净0）
  const shown = counted.filter(r=>!r._hide);          // 展示层不含台账行
  const total = counted.reduce((s,r)=>s+r.amt,0);
  const mm = {}; months.forEach(mo=>mm[mo]=counted.filter(r=>r.ym===mo).reduce((s,r)=>s+r.amt,0));

  document.getElementById('kpis').innerHTML =
    K('净开销(3-9月,含房贷)', money(total), 'N + 房贷77,000') +
    K('月均', money(total/months.length), months.length+'个月') +
    K('房贷月供', money(counted.filter(r=>r.cat1==='房贷月供').reduce((s,r)=>s+r.amt,0)), '7笔·补录') +
    K('已对冲组', new Set(recs.filter(r=>r.offsetGroup).map(r=>r.offsetGroup)).size+' 组', '退款/过卡/还款') +
    K('待复核', recs.filter(r=>r.misclassified).length+' 行', '表格R列标"错误"') +
    K('已人工确认', recs.filter(r=>r.reviewed).length+' 行', '表格R列标"确认"');

  // ===== 三分类法横排 =====
  let triMain='', triSub='';
  for(const sk of ['GB','QS','ZFB']){
    const agg={};
    shown.forEach(r=>{const c=r['cat'+sk][0];agg[c]=(agg[c]||0)+r.amt});
    const ent=Object.entries(agg).sort((a,b)=>b[1]-a[1]);
    const colors={}; ent.forEach(([c])=>colors[c]=cColor(sk,c));
    const pieData=ent.filter(e=>e[1]>0);
    const lg=pieData.slice(0,9).map(([c,s])=>
      `<div style="cursor:pointer" onclick="setSchemeAndFilter('${sk}','${c.replace(/'/g,"\\\\'")}')"><span class="sw" style="background:${cColor(sk,c)}"></span>${c} ${(Math.abs(s)/total*100).toFixed(1)}%</div>`).join('');
    const bars=ent.map(([c,s])=>
      `<div class="bar-row" onclick="setSchemeAndFilter('${sk}','${c.replace(/'/g,"\\\\'")}')"><div class="bar-label">${c}</div><div class="bar-track"><div class="bar-fill" style="width:${Math.abs(s)/ent[0][1]*100}%;background:${cColor(sk,c)}"></div></div><div class="bar-val">${money(s)}</div></div>`).join('');
    triMain+=`<div class="scheme-col"><h3>${SCHEMES[sk].name} <span class="chip ${curScheme===sk?'on':''}" style="font-size:10px;padding:1px 8px" onclick="setScheme('${sk}')">${curScheme===sk?'主视图':'设为主视图'}</span></h3>
      <div class="pie-wrap">${triView==='pie'?`<div style="position:relative;width:170px;height:170px"><div id="pie${sk}" style="width:100%;height:100%"></div></div>`:''}<div class="pie-legend">${triView==='pie'?lg:''}</div></div>
      ${triView==='bar'?`<div style="margin-top:6px">${bars}</div>`:''}</div>`;
    if(triView==='pie') queueMicrotask(()=>pieChart('pie'+sk, pieData, colors, 170));
    // 子类排行
    const c2m={}; shown.forEach(r=>{const k=r['cat'+sk][1];c2m[k]=(c2m[k]||0)+r.amt});
    const top=Object.entries(c2m).sort((a,b)=>b[1]-a[1]).slice(0,10);
    const mx=top[0]?top[0][1]:1;
    triSub+=`<div class="scheme-col"><h3 style="color:var(--sub);font-weight:600">${SCHEMES[sk].name} · 子类Top10</h3>${top.map(([c,s])=>
      `<div class="bar-row" onclick="setSchemeAndFilter2('${sk}','${c.replace(/'/g,"\\\\'")}')"><div class="bar-label" title="${c}">${c}</div><div class="bar-track"><div class="bar-fill" style="width:${s/mx*100}%;background:${cColor(sk,flt['cat1'+sk]||'')||'#8a94a8'}"></div></div><div class="bar-val">${money(s)}</div></div>`).join('')}</div>`;
  }
  document.getElementById('triMain').innerHTML=triMain;
  document.getElementById('triSub').innerHTML=triSub;

  // ===== 按月分布 =====
  const pts=months.map(mo=>({label:mo, v:mm[mo]}));
  document.getElementById('monthView').innerHTML = mview==='line'
    ? `<div style="position:relative;height:200px"><div id="mLine" style="width:100%;height:100%"></div></div>`
    : (()=>{const mx=Math.max(...Object.values(mm));return months.map(mo=>`<div class="bar-row" onclick="setFlt('month','${mo}')"><div class="bar-label">${mo}</div><div class="bar-track"><div class="bar-fill" style="width:${mm[mo]/mx*100}%;background:#d5443a">${mm[mo]>mx*0.3?money(mm[mo]):''}</div></div><div class="bar-val">${money(mm[mo])}</div></div>`).join('')})();
  if(mview==='line') lineChart('mLine', months, months.map(mo=>mm[mo]), '#d5443a', 200);

  // ===== 按日分布 =====
  const dayAgg={};
  counted.forEach(r=>{const d=r.date.slice(0,10);dayAgg[d]=(dayAgg[d]||0)+r.amt});
  const dayRows=Object.entries(dayAgg).map(([date,v])=>({date,v,ym:r_ym(date)})).sort((a,b)=>a.date<b.date?-1:1);
  function r_ym(d){return d.slice(0,4)+'年'+parseInt(d.slice(5,7))+'月'}
  document.getElementById('dayView').innerHTML=daySVG(dayRows);

  const bc=Object.entries(DATA.billMonthly).sort((a,b)=>MNUM(a[0])-MNUM(b[0])).map(([mo,w])=>`${mo}: 逢${money(w['逢']||0)}/暖${money(w['暖']||0)}`).join(' ｜ ');
  document.getElementById('billCmp').textContent=bc||'无';

  renderMonthly();
  renderRecon();
  renderRules();
  renderSearch();
}
function onPieClick(sk, lbl){ setSchemeAndFilter(sk, lbl); }
function onLineClick(cid, lbl){ if(cid==='mLine') setFlt('month', lbl); }
function onDayDotClick(day){ /* 点气泡=按日深挖：可扩展 */ }
// ===== 按日分布（Chart.js：选月 + 折线/散点切换，hover 显示数值）=====
let dayMonth = null;
let dview = 'line';
function setDView(v){dview=v;document.querySelectorAll('#dToggle span').forEach(s=>s.classList.remove('on'));event.target.classList.add('on');render()}
function setDayMonth(m){dayMonth=m;render()}
function daySVG(rows){
  if(!dayMonth) dayMonth = months[months.length-1] || '2026年9月';
  const pick=document.getElementById('dayMonthPick');
  if(pick) pick.innerHTML=`<span class="mini" style="align-self:center">月份：</span>`+months.map(m=>`<span class="chip ${dayMonth===m?'on':''}" onclick="setDayMonth('${m}')">${m}</span>`).join('');
  const ds=rows.filter(r=>r.ym===dayMonth).sort((a,b)=>a.date<b.date?-1:1);
  if(!ds.length) return '<div class="note">无数据</div>';
  const max=Math.max(...ds.map(d=>d.v));
  const total=ds.reduce((s,d)=>s+d.v,0);
  const head=`<div style="font-size:11px;color:var(--sub);margin-bottom:4px">${dayMonth} · 净${money(total)} · 最大日净${money(max)} · ${ds.length}天有交易 · <b>hover查看每日数值</b></div>`;
  const labels=ds.map(d=>String(parseInt(d.date.slice(8,10))));
  const vals=ds.map(d=>d.v);
  const holder=`<div style="position:relative;height:${dview==='line'?180:110}px"><div id="${dview==='line'?'dLine':'dDot'}" style="width:100%;height:100%"></div></div>`;
  // 渲染容器后再建图
  requestAnimationFrame(()=>{
    if(dview==='line') lineChart('dLine', labels, vals, '#3a6fd5', 180);
    else dotChart('dDot', labels, vals, '#3a6fd5', 110);
  });
  return head+holder;
}
function setTriView(v){triView=v;document.querySelectorAll('#triToggle span').forEach(s=>s.classList.remove('on'));event.target.classList.add('on');render()}
function setMView(v){mview=v;document.querySelectorAll('#mToggle span').forEach(s=>s.classList.remove('on'));event.target.classList.add('on');render()}
function setScheme(sk){curScheme=sk;render()}
function setSchemeAndFilter(sk,c){curScheme=sk;flt.cat1=c;flt.cat2=null;renderSearch();}
function setSchemeAndFilter2(sk,c){curScheme=sk;flt.cat2=c;renderSearch();}

// ===== 月度分组（分类chips多选：亮=显示 灰=排除；默认排除创业/婚礼）=====
const MG_EXCL_KEYWORDS = ['创业','婚礼'];
function mgIsExcluded(cat){ return MG_EXCL_KEYWORDS.some(k=>cat.includes(k)); }
let mgExcl = null;   // 懒初始化
function mgToggleCat(c){
  if(mgExcl.has(c)) mgExcl.delete(c); else mgExcl.add(c);
  renderMonthly();
}
function mgClearExcl(){ mgExcl.clear(); renderMonthly(); }
function mgSetScheme(sk){curScheme=sk;['GB','QS','ZFB'].forEach(k=>document.getElementById('mgSc'+k)?.classList.toggle('on',k===sk));mgExcl=null;renderMonthly()}
function renderMonthly(){
  const chipsEl=document.getElementById('mgCatChips');
  if(!chipsEl)return;
  const c1m={}; recs.filter(isCounted).forEach(r=>{const c=cat1Of(r);c1m[c]=(c1m[c]||0)+r.amt});
  const cats=Object.entries(c1m).sort((a,b)=>b[1]-a[1]);
  // 懒初始化排除集（切分类法后重置为默认排除）
  if(mgExcl===null) mgExcl = new Set(cats.map(([c])=>c).filter(mgIsExcluded));
  chipsEl.innerHTML=`<span class="mini" style="align-self:center">分类：</span>`+
    `<span class="chip ${mgExcl.size===0?'on':''}" onclick="mgClearExcl()">全部</span>`+
    cats.map(([c,s])=>{
      const off=mgExcl.has(c);
      return `<span class="chip" ${off?'style="opacity:.45;text-decoration:line-through"':`style="background:${cColor(curScheme,c)};border-color:${cColor(curScheme,c)};color:#fff"`} onclick="mgToggleCat('${c.replace(/'/g,"\\\\'")}')" title="${off?'点击恢复显示':'点击排除'}">${c} <span style="opacity:.65;font-size:10px">${money(s)}</span></span>`;
    }).join('');
  let pool=recs.filter(isCounted).filter(r=>!r._hide&&!mgExcl.has(cat1Of(r)));
  if(hidePaired) pool=pool.filter(r=>!r.pairId);
  const byM={}; pool.forEach(r=>{(byM[r.ym]=byM[r.ym]||[]).push(r)});
  const gmax=Math.max(...months.map(mo=>(byM[mo]||[]).reduce((s,r)=>s+r.amt,0)),1);
  let html='';let shown=0;let prevNet=null;
  for(const mo of months){
    const list=(byM[mo]||[]).sort((a,b)=>b.amt-a.amt);
    if(!list.length)continue;
    const net=list.reduce((s,r)=>s+r.amt,0);
    const mom=prevNet===null?null:(net-prevNet)/prevNet*100;
    prevNet=net;shown+=list.length;
    html+=`<div class="monthgrp ${mgOpen[mo]?'open':''}" id="mg-${mo}">
      <div class="mg-head" onclick="toggleMg('${mo}')">
        <span class="m">${mo}</span><span class="net">${money(net)}</span>
        ${mom!==null?`<span class="mom">${mom>=0?'▲':'▼'} ${Math.abs(mom).toFixed(1)}%</span>`:'<span class="mom">首月</span>'}
        <span class="n">${list.length}笔</span>
        <span class="spark"><div style="width:${net/gmax*100}%"></div></span>
      </div>
      <div class="mg-body"><div class="mg-tbl-wrap"><table><thead><tr><th>日期</th><th>人</th><th>交易对象</th><th>分类(${curScheme})</th><th style="text-align:right">金额 ↓</th><th>表格</th></tr></thead><tbody>
      ${list.map(r=>`<tr class="${r.pairId?'paired':''}"><td>${r.date}</td><td>${r.owner}</td><td>${r.counter.slice(0,20)}</td><td><span class="tag" style="background:${cColor(curScheme,cat1Of(r))}22;color:${cColor(curScheme,cat1Of(r))}">${cat1Of(r)}</span> <span class="note">${cat2Of(r)}</span>${r.pairId?`<span class="pairsig">⇄${r.pairId}</span>`:''}${r.partialRefund?'<span class="tag">部分退款净额</span>':''}</td><td style="text-align:right;font-weight:600">${r.pairId?`<span class="strike">${money(r.amt)}</span>`:money(r.amt)}</td><td><a class="tlink" href="${r.sheetLink}" target="_blank">↗</a></td></tr>`).join('')}
      <tr class="mrow-total"><td colspan="4">${mo} 净额（${list.length}笔）</td><td style="text-align:right">${money(net)}</td><td></td></tr>
      </tbody></table></div></div>
    </div>`;
  }
  document.getElementById('monthlyView').innerHTML=html||'<div class="note">无匹配</div>';
  document.getElementById('mgInfo').textContent=`共 ${shown} 笔 · ${SCHEMES[curScheme].name}`;
}
function toggleMg(m){mgOpen[m]=!mgOpen[m];document.getElementById('mg-'+m).classList.toggle('open')}
function mgToggleAll(open){months.forEach(m=>mgOpen[m]=open);document.querySelectorAll('.monthgrp').forEach(el=>el.classList.toggle('open',open))}
function toggleHidePair(){hidePaired=!hidePaired;document.getElementById('hidePairBtn').classList.toggle('on',hidePaired);render()}

// ===== 对账视图（左右分栏双列手风琴，按类型分组，限高滚动）=====
function pairRow(l, r){
  return `<div class="recon-pair">
    <div class="recon-cell L">${l?`<span class="recon-amt-d">-${money(Math.abs(l.amt||0))}</span><div class="recon-note">${l.date||''} ${l.counter||''}</div><div class="recon-note">${l.acct||''}</div>`:'<span class="note">—</span>'}</div>
    <div class="recon-arrow">⇄</div>
    <div class="recon-cell R">${r?`<span class="recon-amt-c">+${money(Math.abs(r.amt||0))}</span><div class="recon-note">${r.date||''} ${r.counter||''}</div><div class="recon-note">${r.acct||''}</div>`:'<span class="note">—</span>'}</div>
  </div>`;
}
function renderRecon(){
  const types=['全部',...new Set(DATA.recon.map(g=>g.type))];
  document.getElementById('reconFilter').innerHTML=types.map(t=>`<span class="chip ${reconType===t?'on':''}" onclick="setReconType('${t}')">${t}${t!=='全部'?` (${DATA.recon.filter(g=>g.type===t).length})`:''}</span>`).join('');
  const list=DATA.recon.filter(g=>reconType==='全部'||g.type===reconType);
  // 按类型分块手风琴
  const byType={};
  list.forEach(g=>{(byType[g.type]=byType[g.type]||[]).push(g)});
  let html='';
  for(const [tp, grps] of Object.entries(byType)){
    const open = reconType!=='全部' ? 'open' : '';
    html+=`<div class="rule ${open}" id="rct-${tp.slice(0,4)}" style="grid-column:1/-1">
      <div class="rule-head" onclick="document.getElementById('rct-${tp.slice(0,4)}').classList.toggle('open')">
        <span class="rid">类型</span><span class="rtitle">${tp}</span><span class="rstat">${grps.length}组</span>
      </div>
      <div class="rule-body" style="max-height:300px;display:${reconType!=='全部'?'block':'none'};padding:6px;background:#fff">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        ${grps.map(g=>{
          const L=Array.isArray(g.left)?g.left:[g.left];
          const R=Array.isArray(g.right)?g.right:[g.right];
          const lAmt=L.reduce((s,x)=>s+Math.abs(x.amt||0),0);
          const rAmt=R.reduce((s,x)=>s+Math.abs(x.amt||0),0);
          const bal=Math.abs(lAmt-rAmt)<0.01;
          const rows=Math.max(L.length,R.length);
          let body='';
          for(let i=0;i<rows;i++){
            body+=pairRow(R[i], L[i]);   // 左列出账(debit侧=right字段是出账) 右列入账
          }
          return `<div class="recon-grp ${reconType!=='全部'?'open':''}" id="rc-${g.gid}" style="cursor:pointer">
            <div class="recon-head" onclick="document.getElementById('rc-${g.gid}').classList.toggle('open')">
              <span class="gid">${g.gid}</span>
              <span style="color:${bal?'var(--green)':'var(--gold)'}">${bal?'✓':'△'+money(lAmt-rAmt)}</span>
              <span class="recon-note">${(g.note||'').slice(0,26)}</span>
            </div>
            <div class="recon-body">${body}</div>
          </div>`;
        }).join('')}
        </div>
      </div>
    </div>`;
  }
  document.getElementById('reconView').innerHTML=html;
  document.getElementById('reconSum').textContent=`${list.length} 组｜${reconType}｜点击组头展开对账明细（左出账⇄右入账）`;
}
function setReconType(t){reconType=t;renderRecon()}

// ===== 去重规则 =====
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function renderRules(){
  document.getElementById('ruleList').innerHTML=DATA.dedup.invisible.map(r=>`
    <div class="rule ${r.flag?'alert':''}" id="rule-${r.id}">
      <div class="rule-head" onclick="document.getElementById('rule-${r.id}').classList.toggle('open')">
        <span class="rid">${r.id}</span><span class="rtitle">${r.title}</span>
        <span class="rstat">${r.n}笔 ${money(r.impact)}</span>
      </div>
      ${r.flag?`<div class="flagline">⚠️ ${r.flag}</div>`:''}
      <div class="rule-body"><table><thead><tr><th>日期</th><th>交易对象</th><th style="text-align:right">金额</th><th>备注</th></tr></thead><tbody>
      ${r.items.slice().sort((a,b)=>b.amt-a.amt).slice(0,50).map(i=>`<tr><td>${i.date}</td><td>${esc(i.counter)}</td><td style="text-align:right;font-weight:600">${money(i.amt)}</td><td class="note">${esc(i.note||'')}</td></tr>`).join('')}
      </tbody></table></div>
    </div>`).join('');
}

// ===== 明细检索（平铺过滤） =====
function setSchemeSearch(sk){curScheme=sk;flt.cat1=null;flt.cat2=null;renderSearch()}
function setFlt(k,v){
  if(k==='cat1'){flt.cat1=flt.cat1===v?null:v;flt.cat2=null}
  else if(k==='cat2')flt.cat2=flt.cat2===v?null:v;
  else if(k==='event')flt.event=flt.event===v?null:v;
  else if(k==='month')flt.month=flt.month===v?null:v;
  renderSearch();
}
function renderSearch(){
  // 分类标准选择
  document.getElementById('searchSchemePick').innerHTML=['GB','QS','ZFB'].map(sk=>
    `<span class="chip ${curScheme===sk?'on':''}" onclick="setSchemeSearch('${sk}')">${SCHEMES[sk].name}</span>`).join('');
  // 主类平铺
  const c1m={}; recs.filter(r=>!r._hide).forEach(r=>{const c=cat1Of(r);c1m[c]=(c1m[c]||0)+r.amt});
  document.getElementById('flatCat1').innerHTML=`<span class="mini" style="align-self:center">主类：</span>`+
    `<span class="chip ${!flt.cat1?'on':''}" onclick="setFlt('cat1',null)">全部</span>`+
    Object.entries(c1m).sort((a,b)=>b[1]-a[1]).map(([c,s])=>
      `<span class="chip ${flt.cat1===c?'on':''}" style="${flt.cat1===c?`background:${cColor(curScheme,c)};border-color:${cColor(curScheme,c)}`:''}" onclick="setFlt('cat1','${c.replace(/'/g,"\\\\'")}')">${c} <span style="opacity:.6;font-size:10px">${money(s)}</span></span>`).join('');
  // 子类平铺
  const c2pool=recs.filter(r=>!r._hide&&(!flt.cat1||cat1Of(r)===flt.cat1));
  const c2m={}; c2pool.forEach(r=>{c2m[cat2Of(r)]=(c2m[cat2Of(r)]||0)+r.amt});
  document.getElementById('flatCat2').innerHTML=flt.cat1?`<span class="mini" style="align-self:center">子类：</span>`+
    `<span class="chip ${!flt.cat2?'on':''}" onclick="setFlt('cat2',null)">全部</span>`+
    Object.entries(c2m).sort((a,b)=>b[1]-a[1]).map(([c,s])=>
      `<span class="chip ${flt.cat2===c?'on':''}" onclick="setFlt('cat2','${c.replace(/'/g,"\\\\'")}')">${c} <span style="opacity:.6;font-size:10px">${money(s)}</span></span>`).join(''):'';
  // 事件
  document.getElementById('flatEv').innerHTML=`<span class="mini" style="align-self:center">事件：</span>`+
    `<span class="chip ${!flt.event?'on':''}" onclick="setFlt('event',null)">全部</span>`+
    events.map(e=>`<span class="chip ${flt.event===e?'on':''}" onclick="setFlt('event','${e}')">${e}</span>`).join('');
  // 月份
  document.getElementById('flatMonth').innerHTML=`<span class="mini" style="align-self:center">月份：</span>`+
    `<span class="chip ${!flt.month?'on':''}" onclick="setFlt('month',null)">全部</span>`+
    months.map(m=>`<span class="chip ${flt.month===m?'on':''}" onclick="setFlt('month','${m}')">${m}</span>`).join('');
  // 表格
  let list=recs.filter(r=>{
    if(r._hide && hidePaired) return false;
    if(flt.cat1&&cat1Of(r)!==flt.cat1)return false;
    if(flt.cat2&&cat2Of(r)!==flt.cat2)return false;
    if(flt.event&&!(r.event||[]).includes(flt.event))return false;
    if(flt.month&&r.ym!==flt.month)return false;
    return true;
  });
  list.sort((a,b)=>{
    let va=sortKey==='schemeCat'?cat1Of(a):sortKey==='schemeCat2'?cat2Of(a):a[sortKey];
    let vb=sortKey==='schemeCat'?cat1Of(b):sortKey==='schemeCat2'?cat2Of(b):b[sortKey];
    if(sortKey!=='amt'){va=Array.isArray(va)?va.join():String(va);vb=Array.isArray(vb)?vb.join():String(vb);return sortDir<0?vb.localeCompare(va):va.localeCompare(vb)}
    return sortDir<0?vb-va:va-vb;
  });
  document.querySelector('#tbl tbody').innerHTML=list.slice(0,400).map(r=>`<tr class="${r.pairId?'paired':''}">
    <td>${r.date}</td><td>${r.owner}</td><td>${r.counter.slice(0,20)}</td>
    <td><span class="tag" style="background:${cColor(curScheme,cat1Of(r))}22;color:${cColor(curScheme,cat1Of(r))}">${cat1Of(r)}</span>${r.pairId?`<span class="pairsig">⇄${r.pairId}</span>`:''}${r.partialRefund?'<span class="tag">部分退款</span>':''}</td>
    <td class="note">${cat2Of(r)}</td><td class="note">${(r.event||[]).join(',')}</td>
    <td style="text-align:right;font-weight:600">${r.pairId?`<span class="strike">${money(r.amt)}</span>`:money(r.amt)}</td>
    <td class="note">${r.offsetGroup?`${r.offsetGroup} ${r.offsetType||''}`:''}</td>
    <td><a class="tlink" href="${r.sheetLink}" target="_blank" title="在腾讯表格中打开此行">↗行${r.sheetRow}</a></td>
  </tr>`).join('');
  document.getElementById('cnt').textContent=list.length+(list.length>400?'+（显示前400）':'');
  document.getElementById('sum').textContent=money(list.filter(isCounted).reduce((s,r)=>s+r.amt,0));
}
function fillSelect(id,opts,cur,none){
  const el=document.getElementById(id);const val=el.value;
  el.innerHTML=`<option value="">${none}</option>`+opts.map(([v,l])=>`<option value="${v}" ${v===cur?'selected':''}>${l}</option>`).join('');
  if(!cur&&val)el.value=val;
}
function showTodo(){
  document.getElementById('todoBox').innerHTML=`<b>v10 变更摘要：</b><br>
  1) <b>1298表已修复</b>：表头第1行；总账单行移入"信用卡月账单汇总验算"表(SHEET_D0xECl)做checksum；每日信用管家10月增量已移除；2076储蓄卡混入行已清<br>
  2) <b>对冲不再加行</b>：明细表 S/T 列标注（对冲组/类型·入账出账）；退款负数行进对账台账（主明细默认隐藏）<br>
  3) <b>对账视图</b>：165组左右对称——退款冲销18·转账退回1·信用卡还款19·渠道/银行双记127<br>
  4) <b>明细跳转</b>：每行 ↗ 打开腾讯表格对应行<br>
  5) R05 待核：1298九月账单应还650.54（验算表⚠行）`;
  document.getElementById('todoBox').scrollIntoView({behavior:'smooth'});
}
document.querySelectorAll('#tbl th').forEach(th=>th.onclick=()=>{
  const k=th.dataset.k;if(!k)return;
  if(sortKey===k){sortDir=-sortDir}else{sortKey=k;sortDir=k==='amt'?-1:1}
  renderSearch();
});
months.forEach(m=>mgOpen[m]=false);
render();
</script>
</body>
</html>"""

out = page.replace('__PAYLOAD__', payload).replace('__CHARTJS__', CHARTJS)
path = '<工作区目录>'
open(path, 'w', encoding='utf-8').write(out)
print('生成:', path, f'({len(out):,} 字符, {len(records)} 条记录, {len(recon)} 对账组)')
