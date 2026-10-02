# -*- coding: utf-8 -*-
"""解密汇丰三份 PDF：密码全部由代码从完整证件/手机/生日/客户号程序化拼接"""
import pikepdf, os, sys

ID_NO = "3209821XX…XXXX7"
PHONE = "1XX…XXXX"
BIRTH = "19950504"          # 身份证第7-14位
CUST_NO = "469018121"       # 汇丰中国客户号

ddmmyyyy = BIRTH[6:] + BIRTH[4:6] + BIRTH[:4]   # 04051995

BASE = "<工作区目录>"

# 信用卡账单：证件后6 + 手机后6（邮件规则）
cc_candidates = [
    ("证件后6+手机后6", ID_NO[-6:] + PHONE[-6:]),
    ("手机后6+证件后6", PHONE[-6:] + ID_NO[-6:]),
]
# 对账单/通知单：生日DDMMYY?YY + 客户号4-9位（邮件写"日日月月年年"=DDMMYY）
stmt_candidates = [
    ("DDMMYYYY+客户4-9位", ddmmyyyy + CUST_NO[3:9]),
    ("DDMMYY+客户4-9位", BIRTH[6:] + BIRTH[4:6] + BIRTH[2:4] + CUST_NO[3:9]),
    ("DDMMYYYY+客户号全", ddmmyyyy + CUST_NO),
]

targets = [
    ("汇丰中国信用卡-电子账单-202609.pdf", cc_candidates),
    ("汇丰中国-电子对账单-20260909.pdf", stmt_candidates),
    ("汇丰中国-电子通知单-20260907.pdf", stmt_candidates),
]

for fname, cands in targets:
    src = os.path.join(BASE, fname)
    print("\n>>", fname)
    ok = False
    for label, pwd in cands:
        try:
            pdf = pikepdf.open(src, password=pwd)
        except Exception as e:
            print(f"   x [{label}] {pwd} -> {type(e).__name__}")
            continue
        out = src.replace(".pdf", "-已解密.pdf")
        pdf.save(out)
        print(f"   OK [{label}] 密码={pwd} 页数={len(pdf.pages)} -> {os.path.basename(out)}")
        ok = True
        break
    if not ok:
        print("   ALL CANDIDATES FAILED")
