#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_proposals.py
----------------------
Runs on a schedule via GitHub Actions (separate from auto_publish.py).
Reads customer leads collected by the WhatsApp webhook (whatsapp_webhook/app.py)
from the shared Google Sheet, and for every lead still marked "جديد" (new):

  1. Drafts a professional commercial-proposal document with Claude, based
     only on what the customer actually said (no invented pricing/promises).
  2. Saves it as a .docx file and uploads it as a GitHub Release asset to get
     a shareable link.
  3. Sends you (not the customer) a WhatsApp message with that link, so you
     can review and decide what to actually send/quote.
  4. Marks the row "تمت الصياغة" so it is not processed twice.

Nothing here contacts the customer directly or commits to a price — by
design, per your earlier decision that proposals are for YOUR review only.

Required environment variables:
  GOOGLE_SERVICE_ACCOUNT_JSON  same service account JSON used by the webhook
  GOOGLE_SHEET_ID
  GOOGLE_SHEET_TAB                default "Leads"
  ANTHROPIC_API_KEY
  ANTHROPIC_MODEL                 default "claude-sonnet-5"
  WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_TO_NUMBER
                                   reused from auto_publish.py's notification feature
  GITHUB_TOKEN, GITHUB_REPOSITORY provided automatically inside GitHub Actions
"""

import os
import json
import pathlib
import subprocess
import tempfile
import uuid

import requests
import anthropic
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from docx import Document

GRAPH_API_VERSION = "v21.0"


def get_sheet():
    raw_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(raw_json)
    creds = ServiceAccountCredentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    tab_name = os.environ.get("GOOGLE_SHEET_TAB", "Leads")
    return client.open_by_key(sheet_id).worksheet(tab_name)


def draft_proposal_text(lead_row):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

    prompt = f"""اكتب مسودة عرض تجاري احترافي بالعربية الفصحى موجّه لصاحب العمل (وليس للعميل
مباشرة — هذه مسودة داخلية للمراجعة فقط)، بناءً على معطيات الطلب التالية التي جُمعت من
محادثة واتساب مع العميل:

اسم العميل: {lead_row.get('اسم العميل', 'غير محدد')}
ملخص الطلب: {lead_row.get('ملخص الطلب', '')}
الكمية/المواصفات: {lead_row.get('الكمية/المواصفات', 'غير محدد')}
الميزانية/الجدول الزمني: {lead_row.get('الميزانية/الجدول الزمني', 'غير محدد')}

اكتب المسودة بالأقسام التالية:
1. ملخص الطلب
2. ما هو مطلوب تحديداً (بصياغة واضحة قابلة للمراجعة السريعة)
3. نقاط يجب على صاحب العمل تحديدها بنفسه قبل الإرسال (مثل السعر النهائي، مدة
   التسليم، أي شروط خاصة) — لا تخترع أرقاماً أو التزامات من عندك أبداً.
4. اقتراح صياغة جاهزة (نص عرض) يمكن لصاحب العمل تعديله وإرساله للعميل، يترك فيها
   فراغات واضحة مثل [السعر] و[مدة التسليم] ليملأها صاحب العمل بنفسه.

أعد فقط نص المسودة، بدون أي تعليق إضافي خارج الأقسام الأربعة."""

    response = client.messages.create(
        model=model,
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()


def build_docx(lead_row, proposal_text, out_path):
    doc = Document()
    doc.add_heading(f"مسودة عرض تجاري — {lead_row.get('اسم العميل', 'عميل غير محدد')}", level=1)
    doc.add_paragraph(f"رقم العميل على واتساب: {lead_row.get('رقم العميل', 'غير متوفر')}")
    doc.add_paragraph(f"تاريخ الطلب: {lead_row.get('التاريخ', 'غير متوفر')}")
    doc.add_paragraph("")  # spacer
    for block in proposal_text.split("\n\n"):
        doc.add_paragraph(block.strip())
    doc.save(out_path)


def upload_as_github_release_asset(file_path):
    repo = os.environ["GITHUB_REPOSITORY"]
    tag = f"proposal-{uuid.uuid4().hex[:10]}"
    subprocess.run(
        ["gh", "release", "create", tag, str(file_path), "--repo", repo,
         "--title", tag, "--notes", "Auto-generated draft commercial proposal."],
        check=True,
    )
    result = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo, "--json", "assets"],
        check=True, capture_output=True, text=True,
    )
    assets = json.loads(result.stdout)["assets"]
    return assets[0]["url"]


def send_whatsapp_notification(title, url):
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    to_number = os.environ.get("WHATSAPP_TO_NUMBER")
    if not (phone_number_id and token and to_number):
        print("[whatsapp] skipped (notification feature not configured)")
        return

    api_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": f"📋 مسودة عرض تجاري جديدة جاهزة للمراجعة:\n{title}\n{url}"},
    }
    resp = requests.post(
        api_url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=20
    )
    if resp.status_code != 200:
        print(f"[whatsapp] خطأ {resp.status_code}: {resp.text[:300]}")


def main():
    sheet = get_sheet()
    records = sheet.get_all_records()  # list of dicts, one per row, keyed by header

    new_rows = [
        (i, row) for i, row in enumerate(records, start=2)  # row 1 is the header
        if row.get("الحالة") == "جديد"
    ]

    if not new_rows:
        print("لا توجد طلبات جديدة لصياغة عروض لها.")
        return

    for row_number, lead_row in new_rows:
        try:
            print(f"[info] جارٍ صياغة عرض لـ: {lead_row.get('اسم العميل')}")
            proposal_text = draft_proposal_text(lead_row)

            with tempfile.TemporaryDirectory() as tmp_dir:
                docx_path = pathlib.Path(tmp_dir) / "proposal.docx"
                build_docx(lead_row, proposal_text, docx_path)
                url = upload_as_github_release_asset(docx_path)

            send_whatsapp_notification(
                lead_row.get("اسم العميل", "عميل غير محدد"), url
            )
            sheet.update_cell(row_number, 7, "تمت الصياغة")  # column 7 = "الحالة"
            print(f"[ok] تم إنشاء المسودة وإرسال الإشعار — {url}")

        except Exception as exc:  # noqa: BLE001
            print(f"[error] فشلت صياغة عرض الصف {row_number}: {exc}")


if __name__ == "__main__":
    main()
