#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
whatsapp_webhook/app.py
------------------------
A small always-on web server (deployed separately from the GitHub Actions
part of this project — see README "الجزء الثاني") that:

  1. Receives incoming customer messages via the WhatsApp Business Platform
     (Cloud API) webhook.
  2. Holds a conversation with the customer using Claude, asking the
     clarifying questions needed to understand what they want (product or
     service, quantity/specs, any budget or timeline they mention).
  3. Once enough information is gathered, saves one structured row to a
     Google Sheet (so YOU can review it personally — nothing is sent back
     to the customer as a commercial offer automatically) and replies to the
     customer with a short confirmation message.

This file is intentionally a single, readable module rather than a
multi-file framework, since it is small enough to review end-to-end in one
sitting — that matters here because this handles real customer
conversations.

Required environment variables:
  WHATSAPP_VERIFY_TOKEN     any string you invent; must match what you type
                             into the Meta webhook configuration screen
  WHATSAPP_ACCESS_TOKEN     permanent System User token for the Cloud API
  WHATSAPP_PHONE_NUMBER_ID  the Cloud API "from" phone number ID
  ANTHROPIC_API_KEY         required — this feature needs Claude to run
  ANTHROPIC_MODEL           default "claude-sonnet-5"
  GOOGLE_SERVICE_ACCOUNT_JSON  the full JSON key of a Google service account,
                             as a single-line string (see README)
  GOOGLE_SHEET_ID           the spreadsheet ID that stores collected leads
  GOOGLE_SHEET_TAB          default "Leads"
"""

import os
import json
import datetime

from flask import Flask, request, jsonify
import requests
import anthropic
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

app = Flask(__name__)

GRAPH_API_VERSION = "v21.0"

# In-memory conversation state, keyed by the customer's WhatsApp number.
# NOTE: this resets if the server restarts — acceptable for this use case
# (a lost mid-conversation state just means the customer is asked the
# clarifying questions again), but it does mean you should run this on a
# host that does not sleep/restart the process mid-conversation if you can
# help it. A production-grade version would persist this in a database
# instead; flagged here rather than silently hidden.
CONVERSATIONS = {}

SYSTEM_PROMPT = """أنت مساعد مبيعات ذكي ومهذب يعمل نيابة عن صاحب العمل عبر واتساب.
مهمتك الوحيدة هي محادثة العميل بأسلوب ودود واحترافي لفهم ما يحتاجه بالضبط، عبر طرح
أسئلة توضيحية قصيرة واحداً تلو الآخر (وليس كلها دفعة واحدة). اجمع هذه المعلومات:
- ما هو المنتج أو الخدمة التي يريدها العميل بالضبط
- الكمية أو المواصفات إن وجدت
- أي ميزانية أو جدول زمني يذكره العميل من تلقاء نفسه (لا تُلحّ على سؤاله عن الميزانية
  أكثر من مرة واحدة إن لم يرغب بالإفصاح عنها)
- اسم العميل إن لم يكن معروفاً

لا تُقدّم أي أسعار أو عروض أو التزامات نيابة عن صاحب العمل أبداً — فقط اجمع المعلومات.
بمجرد أن تشعر أن لديك صورة كافية عن طلب العميل (حتى لو لم تحصل على كل التفاصيل)، أنهِ
ردّك بسطر منفصل بالضبط بهذا الشكل (لا تُضف أي نص آخر على نفس السطر):
[LEAD_READY]{"customer_name": "...", "request_summary": "...", "quantity_or_specs": "...", "budget_or_timeline": "..."}

استخدم "غير محدد" لأي حقل لم يذكره العميل. اكتب الحقول بالعربية. إن لم يكن الطلب
جاهزاً بعد، لا تُضف سطر [LEAD_READY] إطلاقاً، وتابع طرح الأسئلة بشكل طبيعي."""


# --------------------------------------------------------------------------
# Google Sheets
# --------------------------------------------------------------------------
def get_sheet():
    raw_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(raw_json)
    creds = ServiceAccountCredentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    tab_name = os.environ.get("GOOGLE_SHEET_TAB", "Leads")
    spreadsheet = client.open_by_key(sheet_id)
    try:
        return spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=8)
        ws.append_row(
            ["التاريخ", "رقم العميل", "اسم العميل", "ملخص الطلب",
             "الكمية/المواصفات", "الميزانية/الجدول الزمني", "الحالة"]
        )
        return ws


def save_lead(customer_number, lead):
    sheet = get_sheet()
    sheet.append_row(
        [
            datetime.datetime.utcnow().isoformat(),
            customer_number,
            lead.get("customer_name", "غير محدد"),
            lead.get("request_summary", ""),
            lead.get("quantity_or_specs", "غير محدد"),
            lead.get("budget_or_timeline", "غير محدد"),
            "جديد",
        ]
    )


# --------------------------------------------------------------------------
# Claude conversation
# --------------------------------------------------------------------------
def get_claude_reply(customer_number, incoming_text):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

    history = CONVERSATIONS.setdefault(customer_number, [])
    history.append({"role": "user", "content": incoming_text})

    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=history,
    )
    reply_text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()

    history.append({"role": "assistant", "content": reply_text})

    lead = None
    visible_reply = reply_text
    marker = "[LEAD_READY]"
    if marker in reply_text:
        before, _, after = reply_text.partition(marker)
        visible_reply = before.strip()
        try:
            lead = json.loads(after.strip())
        except json.JSONDecodeError:
            lead = None  # model formatted it slightly wrong; log it, don't crash
            print(f"[warn] تعذّر تحليل JSON الخاص بالطلب: {after[:200]}")

    return visible_reply, lead


# --------------------------------------------------------------------------
# WhatsApp Cloud API
# --------------------------------------------------------------------------
def send_whatsapp_text(to_number, text):
    phone_number_id = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
    token = os.environ["WHATSAPP_ACCESS_TOKEN"]
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=20,
    )
    if resp.status_code != 200:
        print(f"[whatsapp-send] خطأ {resp.status_code}: {resp.text[:300]}")


# --------------------------------------------------------------------------
# Flask routes
# --------------------------------------------------------------------------
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    expected_token = os.environ.get("WHATSAPP_VERIFY_TOKEN")

    if mode == "subscribe" and token == expected_token:
        return challenge, 200
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json(silent=True) or {}

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        messages = value.get("messages")
        if not messages:
            # Could be a delivery/read status update — nothing to do.
            return jsonify({"status": "ignored"}), 200

        message = messages[0]
        customer_number = message["from"]
        message_type = message.get("type")

        if message_type != "text":
            send_whatsapp_text(
                customer_number,
                "شكراً لرسالتك! حالياً أستطيع التعامل مع الرسائل النصية فقط — "
                "هل يمكنك وصف طلبك في رسالة نصية؟",
            )
            return jsonify({"status": "ok"}), 200

        incoming_text = message["text"]["body"]

        reply_text, lead = get_claude_reply(customer_number, incoming_text)

        if reply_text:
            send_whatsapp_text(customer_number, reply_text)

        if lead:
            save_lead(customer_number, lead)
            send_whatsapp_text(
                customer_number,
                "تم تسجيل طلبك بنجاح، شكراً لك! سيراجعه فريقنا قريباً.",
            )
            CONVERSATIONS.pop(customer_number, None)  # reset for next time

    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected payload shape crash the webhook — Meta will
        # retry failed webhooks aggressively, which can spiral quickly.
        print(f"[webhook] خطأ غير متوقع أثناء معالجة الرسالة: {exc}")

    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def health_check():
    return "WhatsApp lead-collection webhook is running.", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
