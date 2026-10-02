# -*- coding: utf-8 -*-
"""用 gen_dashboard.py 的页面模板 + demo 数据渲染 demo 仪表盘 HTML
方式：导入模板字符串（page 变量），替换 PAYLOAD/CHARTJS，输出 docs/index.html
"""
import json, os, sys

WS = os.environ.get('DASH_WS', '<你的工作区目录>')  # 存放 gen_dashboard.py 与 assets/chart.umd.min.js 的目录
HERE = os.path.dirname(os.path.abspath(__file__))

# 读模板：取 gen_dashboard.py 源码里的 page 字符串
src = open(f'{WS}/gen_dashboard.py', encoding='utf-8').read()
i0 = src.find('page = """') + len('page = """')
end_marker = '</html>"""'
i1 = src.find(end_marker)
assert i1 > i0, 'template end marker not found'
page = src[i0:i1] + '</html>'
# 边界自检：绝不能把 Python 尾巴带进模板
assert 'page.replace' not in page and page.count('</html>') == 1, 'template boundary broken'

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
