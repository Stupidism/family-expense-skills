# -*- coding: utf-8 -*-
"""v10.4 明细行链接升级：
用户验证的有效格式：?tab=SHEET_6TgC25&type=1&rangeid=<选区ID>
rangeid 是服务端选区快照ID，无法本地构造任意行。
方案（两全）：
  1) 每行链接 = 官方"跳转单元格"超链接的等价物——在腾讯表格 U 列（col 20，T列后一列）
     给每行生成 set_link？—— 1108 次 API 调用太多，且那是表内导航。
  2) 务实方案（采纳）：仪表盘链接用 ?tab=SHEET_6TgC25&type=1&u= 格式不可行 →
     保持 tab 定位 + 行号即点即见（title + 链接文本"↗行N"），打开后 Ctrl+G A{N} 一秒到位。
     同时把 type=1 参数补上（用户链接里带，可能是"普通表格视图"标志）。
"""
import json

BASE = "<工作区目录>"
SHEET_URL = "https://docs.qq.com/sheet/YOUR_DOC_URL_TOKEN"
DETAIL_SHEET = "SHEET_6TgC25"

recs = json.load(open(f"{BASE}/_v10_rows.json"))
for i, r in enumerate(recs):
    row = i + 2  # Excel行号
    # 用户验证格式：tab + type=1（rangeid 无法逐行构造，省略后定位到 sheet 顶部，Ctrl+G 跳行）
    r['sheetLink'] = f"{SHEET_URL}?_fid=YOUR_FILE_ID&tab={DETAIL_SHEET}&type=1"
    r['sheetRow'] = row

json.dump(recs, open(f"{BASE}/_v10_rows.json", 'w'), ensure_ascii=False, indent=1)
print(f"链接已升级为 ?tab={DETAIL_SHEET}&type=1 格式（{len(recs)} 行）")
print("说明：rangeid 为服务端选区快照ID，无法本地按行构造；")
print("每行链接仍带 ↗行N 提示，打开表格后 Ctrl+G 输入 A{行号} 精确跳转。")
