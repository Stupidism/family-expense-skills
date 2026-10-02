---
name: tencent-sheet-sync
description: 腾讯文档表格读写同步。通过 tencent-docs skill 的 sheet-mcp 对《家庭资产配置总表》批量写入/清除/下拉验证/查找/行号定位，含全量重写明细表、设置分类下拉、账单验算表勾稽等操作规范。当需要把本地数据写回腾讯表格、设置数据验证下拉、或排查表格读写问题时使用。
agent_created: true
---

# 腾讯文档表格同步

调用通道：tencent-docs skill → `tencentdocs.py tdoc_call sheet-mcp <tool> '<json>'`（cwd=skill目录）
Python 固定用 `<python3>`
file_id=`YOUR_FILE_ID`；sheet_id 映射见 family-expense-hub/references/sheet-map.md

## 写入规范

1. **先 clear 后写**：`clear_range_cells {start_row:0, end_row:实际行数+100, start_col:0, end_col:21}`——set_range_value_by_csv 不覆盖旧行，残留行=重复计算（血泪教训）
2. **批量**：150行/批循环 set_range_value_by_csv；CSV 每行列数必须一致
3. **列模式验证**：`set_data_validation {type:"LIST", col_indexes:[{start,end}], ignore_rows:1, select_options:[{id,text,bg_color,text_color}]}`——新行自动继承
4. 大批量重写走"备用表 SHEET_hsgpLC → 核对 → 替换正式表"双保险

## 明细表（SHEET_6TgC25）下拉配置现状

- K/M/O 主类：LIST 静态选项（GB18/QS14/ZFB13项）
- L/N/P 子类：LIST "主类｜子类"分组格式+同主类同底色（18色板 PALETTE）——API 无 INDIRECT 级联的替代方案
- Q 事件：MULTIPLE_LIST（婚礼/配偶手术及康复/旅游/Deel离职）
- R 复核：LIST（确认/错误/GB主类=等模板）
- 重建脚本：工作区 `set_dropdowns.py`（主类/R列）+ `set_grouped_dropdowns.py`（子类分组）

## 读取

- `get_cell_data`：返回 cells 数组（row/col 0-based + string_value/number_value），自行组装行；大范围分页读
- `find {search_term, max_results}`：无 sheet_id 参数，全文档搜（用于行号定位验证写入对齐）

## 已知坑（实测）

| 坑 | 解法 |
|---|---|
| add_sheet 报 row_count 不支持 | 只传 name + append_index |
| search_data 工具不存在 | 用 find |
| get_sheet_info 不收 sheet_id | 用 get_dimension_size(type:"row"/"col") 探行数 |
| set_link 只写普通URL | 无法生成官方"跳转单元格"链接（rangeid不可构造） |
| 验证规则无读回API | 以调用回执无 error 为准 |
| 操作超表边界报608698 | 列号≤21、行号≤实际+缓冲 |

## 跳转链接格式（仪表盘↔表格）

- 可用：`https://docs.qq.com/sheet/YOUR_DOC_URL_TOKEN?_fid=YOUR_FILE_ID&tab=SHEET_6TgC25&type=1`（切表有效）
- 不可用：x/y/c/u/rangeid 均无法定位单元格（rangeid=服务端选区快照ID）
- 行定位：打开后 Ctrl+G 输入 A{行号}；仪表盘每行"↗行N"标注行号

## 验算表勾稽（SHEET_D0xECl）

每期账单入表后更新该表：`应还金额` vs `周期内明细合计` → 差额=0 为 ✓平衡；新账单月加一行；出账前"未出账"；卡明细表严禁混入账单汇总行（用户废除）
