# -*- coding: utf-8 -*-
"""apply_review.py —— 从腾讯文档明细表读回用户手动复核(R列)，覆盖 _v9_rows.json 的自动分类
用法：用户在表格 R 列填：
  - "错误"                     → 标记识别错误（不改分类，仅打标）
  - "确认"                     → 标记已核对
  - "GB主类=xxx"               → 覆盖 GB 主类
  - "GB子类=xxx; QS主类=yyy"   → 分号分隔多项覆盖
  - "GB=食品烟酒/餐饮外卖"      → 主类/子类 一次覆盖
下次生成仪表盘前先跑本脚本。
"""
import json, subprocess, csv, io, re, sys

PY = "<python3>"
SKILL = "<user>/.workbuddy/plugins/cache/workbuddy-builtin/tencent-docs-plugin/5.5.4-wb.38151288.g1ca4889a.hde0fbd244c72/skills/tencent-docs"
FILE_ID = "YOUR_FILE_ID"
SHEET = "SHEET_6TgC25"
BASE = "<工作区目录>"

def call(tool, args):
    r = subprocess.run([PY, "tencentdocs.py", "tdoc_call", "sheet-mcp", tool, json.dumps(args, ensure_ascii=False)],
                       capture_output=True, text=True, cwd=SKILL, timeout=300)
    return r.stdout

def read_col(col, start_row, end_row):
    """读一列（R=17）"""
    out = call("get_cell_data", {"file_id": FILE_ID, "sheet_id": SHEET, "start_row": start_row, "end_row": end_row, "start_col": col, "end_col": col})
    d = json.loads(out)
    cells = json.loads(d['result']['content'][0]['text'])['cells']
    return {c['row']: c.get('string_value', '') for c in cells if c.get('string_value')}

def main():
    recs = json.load(open(f'{BASE}/_v9_rows.json'))
    # 读 R 列（col 17）第1-918行
    reviews = read_col(17, 1, 918)
    applied, flagged = 0, 0
    for i, r in enumerate(recs):
        rv = reviews.get(i + 1, '').strip()  # 行号 = 数据索引+1（0是表头）
        if not rv: continue
        r['review'] = rv
        if rv == '确认':
            r['reviewed'] = True
            continue
        if rv == '错误':
            r['misclassified'] = True
            flagged += 1
            continue
        # 解析覆盖
        for part in re.split(r'[;；]', rv):
            part = part.strip()
            # 新格式：'主类｜子类'（子类下拉选项）——按包含'｜'自动识别并写入对应 scheme
            m_pipe = re.match(r'(.+?)[｜|]\s*(.+)', part)
            m = re.match(r'(GB|QS|ZFB)(主类|子类)?[=＝](.+)', part)
            if m_pipe and not m:
                # 从表格列判断用户改的是哪套分类（无法直接知道，写 GB+QS+ZFB 三套同步）
                c1, c2 = m_pipe.group(1).strip(), m_pipe.group(2).strip()
                r['catGB'] = [c1, c2]; r['catQS'] = [c1, c2]; r['catZFB'] = [c1, c2]
                applied += 3
                continue
            m2 = re.match(r'(GB|QS|ZFB)[=＝]([^/／]+)/(.+)', part)
            if m2:
                scheme, c1, c2 = m2.group(1), m2.group(2).strip(), m2.group(3).strip()
                key = 'cat' + scheme
                r[key] = [c1, c2]
                applied += 1
            elif m:
                scheme, level, val = m.group(1), m.group(2), m.group(3).strip()
                key = 'cat' + scheme
                idx = 0 if (level == '主类' or level is None) else 1
                lst = r[key]
                lst[idx] = val
                r[key] = lst
                applied += 1
    json.dump(recs, open(f'{BASE}/_v9_rows.json', 'w'), ensure_ascii=False, indent=1)
    print(f'复核读取完成：覆盖 {applied} 项，标记错误 {flagged} 行，确认 {sum(1 for r in recs if r.get("reviewed"))} 行')

if __name__ == '__main__':
    main()
