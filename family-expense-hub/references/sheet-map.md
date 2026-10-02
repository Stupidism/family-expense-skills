# 腾讯文档《家庭资产配置总表》结构映射

- 文档：https://docs.qq.com/sheet/YOUR_DOC_URL_TOKEN ｜ file_id=YOUR_FILE_ID
- 编辑方式：tencent-docs skill → tencentdocs.py tdoc_call sheet-mcp <tool>
- Python：<python3>

## 卡明细表（真相层，只追加）

| sheet_id | 表名 |
|---|---|
| SHEET_QBuvqA | 逢招行9876（借记） |
| SHEET_J1haPg | 逢招行信用卡1298 |
| SHEET_0qjmKP | 逢中信3829 |
| SHEET_xlcOss | 逢中行5436 |
| SHEET_WXaEji | 暖招行8316（借记） |
| SHEET_H6M1yF | 暖招行信用卡7623 |
| SHEET_jhHMFE | 暖农行1479 |
| SHEET_ILxU2r | 逢汇丰HK储蓄 |
| SHEET_huiA37 | 逢汇丰HK卡 |
| SHEET_vNM7N3 | 逢微信渠道 |
| SHEET_olBhUY | 暖微信渠道 |
| SHEET_4wfvgd | 逢支付宝渠道 |
| SHEET_BcCfe7 | 暖支付宝渠道 |
| SHEET_hsgpLC | 备用表（整批重写的中转核对） |
| SHEET_LWCVGb | 贵金属明细 |

## 汇总层

| sheet_id | 表名 | 结构 |
|---|---|---|
| SHEET_6TgC25 | 开销流水明细（正式） | A-T 20列：月份/日期/归属/支付账户/机构商户/用途分类/金额/币种/数据来源/备注/GB主类/GB子类/QS主类/QS子类/ZFB主类/ZFB子类/事件标签/复核/对冲组/对冲状态 |
| SHEET_OVB5sa | 每月开销汇总 | SUMIFS 引明细表，D:J 全公式 |
| SHEET_D0xECl | 信用卡月账单汇总验算 | 卡/账单月/周期/应还/明细合计/差额/状态/说明（checksum专用） |
| SHEET_dcpMyb | 分类法字典 | 三分类法定义+使用说明 |

## 明细表 SHEET_6TgC25 列规范

- 行号：第1行表头，数据从第2行（0-based row=1）起；仪表盘 ↗行N 链接 = ?tab=SHEET_6TgC25&type=1
- K-P 列：三分类（LIST 下拉已设；L/N/P 子类选项=“主类｜子类”分组格式+同组同底色）
- Q 列事件：MULTIPLE_LIST（婚礼/配偶手术及康复/旅游/Deel离职）
- R 列复核：用户填——"确认"/"错误"/"主类｜子类"(三套同步)/"GB主类=xx"（apply_review.py 解析）
- S/T 列：对冲组ID/对冲状态（类型·入账出账/已对冲Gxxx/含部分退款净额/对账台账）
- 写入：set_range_value_by_csv 批量150行/批；**先 clear_range_cells**（end_row=实际+100, end_col=21）

## 关键工具坑

- add_sheet 参数是 name（非 title）；无 row_count
- get_cell_data 返回 cells 数组需自组行；大范围读分页
- find 工具无 sheet_id 参数（全文档搜）
- set_data_validation：LIST/MULTIPLE_LIST 仅静态 select_options（无 INDIRECT 级联）；col_indexes 列模式+ignore_rows=1 新行自动继承
- 跳转链接：URL 无单元格定位参数（rangeid 为服务端选区快照ID不可构造）；tab 参数有效，Ctrl+G 跳行
