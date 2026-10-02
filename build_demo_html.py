# -*- coding: utf-8 -*-
"""用 gen_dashboard.py 的页面模板 + demo 数据渲染 demo 仪表盘 HTML
方式：导入模板字符串（page 变量），替换 PAYLOAD/CHARTJS，输出 docs/index.html
"""
import json, os, sys

WS = '/Users/sunmer/WorkBuddy/2026-09-23-12-35-30'
HERE = os.path.dirname(os.path.abspath(__file__))

# 读模板：取 gen_dashboard.py 源码里的 page 字符串
src = open(f'{WS}/gen_dashboard.py', encoding='utf-8').read()
i0 = src.find('page = """') + len('page = """')
i1 = src.find('\n"""', i0)
page = src[i0:i1]

demo = json.load(open(f'{HERE}/expense-dashboard/assets/demo_data.json', encoding='utf-8'))
payload = json.dumps(demo, ensure_ascii=False)
chartjs = open(f'{WS}/assets/chart.umd.min.js', encoding='utf-8').read()

# demo 模式调整：标题 + 演示数据角标 + 跳转链接禁用（无真实表格）
out = page.replace('__PAYLOAD__', payload).replace('__CHARTJS__', chartjs)
out = out.replace(
    '<h1>家庭开销分析仪表盘',
    '<h1>家庭开销分析仪表盘 <span style="font-size:12px;background:#fff3cd;color:#856404;border:1px solid #ffeeba;border-radius:6px;padding:2px 10px;vertical-align:middle;margin-left:8px">DEMO · 演示数据</span>')
# 表格跳转链接指向占位文档
out = out.replace('↗行', '↗(demo)')
open(f'{HERE}/docs/index.html', 'w', encoding='utf-8').write(out)
print(f'docs/index.html: {len(out):,} 字符, {len(demo["records"])} 条记录')
