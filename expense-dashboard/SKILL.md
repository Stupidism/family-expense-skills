---
name: expense-dashboard
description: 家庭开销分析仪表盘生成。基于 _v10_rows.json/_v10_recon.json 生成单文件HTML仪表盘（Chart.js图表+三分类对比+对账视图+月度分组+明细检索）。当用户说"重新生成仪表盘/图表改成XX/界面调整/加个视图"时使用；生成器为工作区 gen_dashboard.py。
agent_created: true
---

# 开销分析仪表盘

生成器：工作区 `gen_dashboard.py` → `开销分析仪表盘.html`（单文件，Chart.js 内嵌离线可用，约870KB）
数据源：`账单存档/2026-09/_v10_rows.json`（1194行）+ `_v10_recon.json`（165组）+ `_dedup_audit.json` + `_eml_bills_parsed.json`
再生命令：`python3 gen_dashboard.py && open 开销分析仪表盘.html`
Chart.js 库：`assets/chart.umd.min.js`（4.4.4，jsdelivr下载，已内嵌）

## 页面结构（用户定稿顺序，勿乱动）

1. **六数字 KPI**：净开销/月均/房贷/已对冲组/待复核/已确认
2. **三分类法横排**（GB｜QS｜ZFB 三列）：主类饼图（Chart.js doughnut，hover金额+占比，点击=过滤明细）+子类Top10排行；饼图↔柱状切换
3. **按月分布**（折线 hover 每月净额，↔柱状切换）+ **按日分布**（月份chips选月+折线↔气泡散点切换）
4. **月度趋势·分组明细**（前移）：分类标准GB/QS/ZFB + 分类chips多选（亮=显示 灰=排除；**默认排除创业/婚礼**）+ 每月折叠组内金额降序 + 每行↗行N表格跳转
5. **对账视图**：左右分栏双列（grid 1fr 1fr，max-height 560px滚动）+ 类型手风琴（4类，点击chip自动展开该类全部组）+ 组内一行一条对照（左出账红⇄右入账绿）
6. **去重源头规则**（R01-R17 可展开）
7. **明细检索**：先选分类标准（GB/QS/ZFB chips）→ 主类/子类/事件/月份平铺chips一按即滤（禁下拉）+ 表头点击排序（默认金额降序）

## 交互铁律

- 分类法选择/过滤一律**平铺 chips**，禁止 select 下拉（用户两次点名）
- 图表一律 Chart.js 标准 tooltip（hover 即时数值），禁自绘 SVG title
- 对冲行=灰色删除线+⇄组号；隐藏对账台账行不计展示层但计净额
- "隐藏已对冲行"开关默认开

## 图表技术要点

- `charts{}` 管理实例，render 前 killChart 防泄漏；饼图 render 后 queueMicrotask 建
- daySVG 容器先渲染再 requestAnimationFrame 建图
- 折线 pointBackgroundColor：值≥3000 标红
- tooltip 回调 TOOLTIP_MONEY 统一 money() 格式

## 净额口径（勿混）

- KPI 总额 = 含隐藏负行（对冲净0后）= 当前 N
- 饼图/排行 = 不含隐藏行
- 月度分组默认排除创业+婚礼后另有合计

## 已验证功能（回归清单）

饼↔柱切换｜月折线↔柱｜按日选月+折线↔气泡｜对账类型展开（还款19组）｜明细QS人情过滤｜月度分组房贷7月组｜↗链接可达｜chips多选排除默认创业婚礼｜hover tooltip 三图表数值
