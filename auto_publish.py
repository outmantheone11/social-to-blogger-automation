#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_publish.py
----------------
Pulls the latest posts from a Facebook Page, an Instagram Business account,
and a TikTok account (your own accounts — these APIs do not allow pulling
content from arbitrary/other accounts), then publishes new ones to a
Blogger blog, formatted as clean HTML. Already-published items are tracked
in state/published_ids.json so nothing is posted twice.

All credentials are read from environment variables (set as GitHub Secrets
in the Actions workflow). Nothing is hard-coded.

Required environment variables:
  FB_PAGE_ID            Facebook Page ID
  FB_PAGE_ACCESS_TOKEN  Long-lived Page Access Token (see README)
  IG_USER_ID            Instagram Business Account ID (linked to the FB Page)
  IG_ACCESS_TOKEN       Instagram Graph API access token (usually same as FB)
  TIKTOK_ACCESS_TOKEN   TikTok access token with video.list scope (optional)
  TIKTOK_OPEN_ID        TikTok open_id of the account (optional)
  BLOGGER_BLOG_ID       Numeric Blogger blog ID
  BLOGGER_CLIENT_ID
  BLOGGER_CLIENT_SECRET
  BLOGGER_REFRESH_TOKEN
Optional:
  MAX_ITEMS_PER_SOURCE  default 5
  STATE_FILE            default "state/published_ids.json"

  # Feature: auto-insert new Facebook listings into the "عروض مختارة"
  # section of the landing page (see listings_update.py). Requires
  # ANTHROPIC_API_KEY too (used to classify/extract the listing fields).
  # Leave BLOGGER_PAGE_ID unset to skip this feature entirely.
  BLOGGER_PAGE_ID       the numeric Page ID of the landing page (NOT the
                        blog ID) — find it via pages().list(blogId=...)

  # Feature: Claude-powered rewrite into a polished blog-post style.
  # Leave ANTHROPIC_API_KEY unset to skip this step (original text is used as-is).
  ANTHROPIC_API_KEY
  ANTHROPIC_MODEL           default "claude-sonnet-5"

  # Feature: WhatsApp notification to yourself whenever a new article is published.
  # Leave unset to skip this feature entirely.
  WHATSAPP_PHONE_NUMBER_ID  the Cloud API "from" phone number ID
  WHATSAPP_ACCESS_TOKEN     permanent System User token (see README)
  WHATSAPP_TO_NUMBER        your own WhatsApp number in international format, e.g. 2126XXXXXXXX

  # Feature: auto-generate a short promo video from the post + its images and
  # publish it as a Reel/TikTok video. Leave GENERATE_PROMO_VIDEO unset/"false"
  # to skip this feature entirely (it is the heaviest and most failure-prone part).
  GENERATE_PROMO_VIDEO      "true" to enable, anything else disables it
  GITHUB_TOKEN              provided automatically inside GitHub Actions
  GITHUB_REPOSITORY         provided automatically inside GitHub Actions
"""

import os
import sys
import json
import html
import datetime
import pathlib

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build

import listings_update

MAX_ITEMS_PER_SOURCE = int(os.environ.get("MAX_ITEMS_PER_SOURCE", "5"))
STATE_FILE = pathlib.Path(os.environ.get("STATE_FILE", "state/published_ids.json"))

GRAPH_API_VERSION = "v21.0"


# --------------------------------------------------------------------------
# State (de-duplication)
# --------------------------------------------------------------------------
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[warn] state file {STATE_FILE} is corrupt, starting fresh")
    return {"facebook": [], "instagram": [], "tiktok": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# --------------------------------------------------------------------------
# Fetchers — each returns a list of dicts: id, title, body_html, permalink,
# image_url, published_at (ISO string)
# --------------------------------------------------------------------------
def fetch_facebook_posts():
    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        print("[facebook] skipped (no credentials)")
        return []

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/posts"
    params = {
        "fields": "id,message,created_time,permalink_url,full_picture",
        "limit": MAX_ITEMS_PER_SOURCE,
        "access_token": token,
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"[facebook] API error {resp.status_code}: {resp.text[:300]}")
        return []

    items = []
    for post in resp.json().get("data", []):
        if not post.get("message"):
            continue  # skip posts with no text (e.g. pure link shares with no caption)
        items.append(
            {
                "source": "facebook",
                "id": post["id"],
                "title": (post["message"].strip().split("\n")[0])[:80],
                "body_html": _text_to_html(post["message"]),
                "permalink": post.get("permalink_url", ""),
                "image_url": post.get("full_picture"),
                "published_at": post.get("created_time"),
            }
        )
    return items


def fetch_instagram_posts():
    ig_user_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not ig_user_id or not token:
        print("[instagram] skipped (no credentials)")
        return []

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media"
    params = {
        "fields": "id,caption,permalink,media_url,media_type,timestamp",
        "limit": MAX_ITEMS_PER_SOURCE,
        "access_token": token,
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"[instagram] API error {resp.status_code}: {resp.text[:300]}")
        return []

    items = []
    for media in resp.json().get("data", []):
        caption = media.get("caption", "")
        items.append(
            {
                "source": "instagram",
                "id": media["id"],
                "title": (caption.strip().split("\n")[0] if caption else "منشور إنستغرام جديد")[:80],
                "body_html": _text_to_html(caption) if caption else "",
                "permalink": media.get("permalink", ""),
                "image_url": media.get("media_url"),
                "published_at": media.get("timestamp"),
            }
        )
    return items


def fetch_tiktok_videos():
    token = os.environ.get("TIKTOK_ACCESS_TOKEN")
    open_id = os.environ.get("TIKTOK_OPEN_ID")
    if not token or not open_id:
        print("[tiktok] skipped (no credentials)")
        return []

    # TikTok "Content Posting API" / "Display API" — video.list endpoint.
    # NOTE: TikTok's public API only exposes videos belonging to the
    # authenticated/own account; there is no supported way to pull videos
    # from third-party accounts.
    url = "https://open.tiktokapis.com/v2/video/list/"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "max_count": MAX_ITEMS_PER_SOURCE,
    }
    fields = "id,title,video_description,share_url,cover_image_url,create_time"
    resp = requests.post(f"{url}?fields={fields}", headers=headers, json=body, timeout=30)
    if resp.status_code != 200:
        print(f"[tiktok] API error {resp.status_code}: {resp.text[:300]}")
        return []

    data = resp.json().get("data", {})
    items = []
    for video in data.get("videos", []):
        desc = video.get("video_description") or video.get("title") or "فيديو تيكتوك جديد"
        create_ts = video.get("create_time")
        published_at = (
            datetime.datetime.utcfromtimestamp(create_ts).isoformat() + "Z"
            if create_ts
            else None
        )
        items.append(
            {
                "source": "tiktok",
                "id": str(video.get("id")),
                "title": desc.strip().split("\n")[0][:80],
                "body_html": _text_to_html(desc),
                "permalink": video.get("share_url", ""),
                "image_url": video.get("cover_image_url"),
                "published_at": published_at,
            }
        )
    return items


def _text_to_html(text):
    escaped = html.escape(text or "").strip()
    paragraphs = [f"<p>{line}</p>" for line in escaped.split("\n") if line.strip()]
    return "\n".join(paragraphs)


# --------------------------------------------------------------------------
# Feature: rewrite the raw social caption into a polished blog-post style
# using the Anthropic API. Fully optional — if ANTHROPIC_API_KEY is not set,
# this is skipped and the original text passes through unchanged.
# --------------------------------------------------------------------------
def rewrite_item_with_claude(item):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    raw_text = html.unescape(
        item.get("body_html", "").replace("<p>", "").replace("</p>", "\n")
    ).strip()
    if not api_key or not raw_text:
        return item  # unchanged

    try:
        import anthropic  # imported lazily so the package is only required when used

        client = anthropic.Anthropic(api_key=api_key)
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
        prompt = (
            "أعد صياغة النص التالي، المأخوذ من منشور على وسائل التواصل الاجتماعي، "
            "ليصبح مقالاً قصيراً بأسلوب مدونة احترافي وسلس بالعربية الفصحى، مع عنوان "
            "جذاب في أول سطر. حافظ على المعنى والمعلومات الأساسية ولا تضف معلومات غير "
            "موجودة في النص الأصلي. أعد فقط النص المُعاد صياغته بدون أي تعليق إضافي.\n\n"
            f"النص الأصلي:\n{raw_text}"
        )
        response = client.messages.create(
            model=model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        rewritten = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        if not rewritten:
            return item

        lines = [line.strip() for line in rewritten.split("\n") if line.strip()]
        new_title = lines[0][:80] if lines else item["title"]
        new_body = "\n".join(f"<p>{html.escape(line)}</p>" for line in lines[1:]) or item.get(
            "body_html", ""
        )
        item = dict(item)  # don't mutate the caller's dict in place
        item["title"] = new_title
        item["body_html"] = new_body
        item["rewritten"] = True
    except Exception as exc:  # noqa: BLE001
        print(f"[claude-rewrite] فشل إعادة الصياغة، سيُنشر النص الأصلي — {exc}")
    return item


# --------------------------------------------------------------------------
# Feature: WhatsApp notification to yourself for every newly published post.
# Fully optional — skipped silently if the WhatsApp env vars are not set.
# --------------------------------------------------------------------------
def send_whatsapp_notification(title, url):
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    to_number = os.environ.get("WHATSAPP_TO_NUMBER")
    if not (phone_number_id and token and to_number):
        return  # feature not configured, skip silently

    api_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    message_text = f"✅ تم نشر مقال جديد في المدونة:\n{title}\n{url}"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=20)
        if resp.status_code != 200:
            print(f"[whatsapp] API error {resp.status_code}: {resp.text[:300]}")
        else:
            print("[whatsapp] تم إرسال إشعار بالمقال الجديد.")
    except Exception as exc:  # noqa: BLE001
        print(f"[whatsapp] فشل إرسال الإشعار — {exc}")


# --------------------------------------------------------------------------
# Feature: classify a Facebook post as a real-estate / land listing and
# extract structured fields for the "عروض مختارة" section of the landing
# page (see listings_update.py for the exact schema it expects).
# Fully optional — skipped silently if ANTHROPIC_API_KEY or BLOGGER_PAGE_ID
# is not set, or if Claude decides the post is not a property listing.
# --------------------------------------------------------------------------
LISTING_SYSTEM_PROMPT = """أنت مساعد يحلل منشورات فيسبوك لمكتب وساطة عقارية مغربي، لتحديد
هل المنشور يُعلن عن عقار سكني (شقة/منزل/فيلا/هنغار) أو أرض (سكنية/تجارية/فلاحية/استثمارية)
معروضة للبيع، واستخراج بياناته إن كان كذلك.

أجب حصراً بكائن JSON واحد، بدون أي نص آخر قبله أو بعده.

إن لم يكن المنشور إعلاناً عن عقار أو أرض للبيع (مثلاً: منشور عام، سؤال، خبر، تهنئة...)، أجب فقط:
{"is_listing": false}

إن كان إعلاناً عقارياً، استخرج:
{
  "is_listing": true,
  "category": "residential" أو "land" فقط،
  "media": "res" للسكني، أو "land" للأرض العادية، أو "coast" للأرض ذات الواجهة البحرية فقط،
  "badge": "نص قصير جداً بصيغة 'للبيع · نوع العقار'، مثال: 'للبيع · شقة فاخرة'",
  "title": "عنوان جذاب قصير يصف العقار وموقعه العام",
  "location": "المدينة أو الحي كما ورد في المنشور",
  "area": "المساحة كما وردت، مع وحدتها (مثال: '220 متر مربع' أو '2 هكتار')، أو 'غير محدد' إن لم تذكر",
  "price": "السعر كما ورد، أو 'ثمن قابل للتفاوض' إن لم يُذكر رقم",
  "wa": "جملة عربية قصيرة لبدء محادثة واتساب عن هذا العقار تحديداً، مثال: 'تفاصيل الشقة الفاخرة بحي جليز'"
}

لا تخترع معلومات غير موجودة في النص. استخدم فقط ما ورد فعلاً في المنشور."""


def classify_listing_with_claude(raw_text):
    """Returns a dict matching listings_update's expected schema, or None
    if this post is not a property listing / the feature isn't configured /
    classification failed for any reason. Never raises."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    page_id = os.environ.get("BLOGGER_PAGE_ID")
    if not api_key or not page_id or not raw_text.strip():
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
        response = client.messages.create(
            model=model,
            max_tokens=500,
            system=LISTING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": raw_text}],
        )
        reply_text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        data = json.loads(reply_text)
        if not data.get("is_listing"):
            return None
        return data
    except Exception as exc:  # noqa: BLE001
        print(f"[listing-classify] فشل تحليل المنشور كعقار، سيُتجاهل — {exc}")
        return None


def maybe_update_listings_page(service, raw_text, item):
    """If configured and the post is a property listing, insert it into the
    LISTINGS array on the landing page. Never raises — logs and continues."""
    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    page_id = os.environ.get("BLOGGER_PAGE_ID")
    if not blog_id or not page_id:
        return  # feature not configured, skip silently

    listing = classify_listing_with_claude(raw_text)
    if not listing:
        return

    if item.get("image_url"):
        listing["image_url"] = item["image_url"]

    try:
        inserted = listings_update.insert_listing(service, blog_id, page_id, listing)
        if inserted:
            print(f"[listings] أُضيف عرض جديد إلى صفحة العقارات: {listing['title']}")
        else:
            print("[listings] العرض موجود مسبقاً في الصفحة، تم تجاهله.")
    except Exception as exc:  # noqa: BLE001
        print(f"[listings] فشل تحديث صفحة العقارات — {exc}")


# --------------------------------------------------------------------------
# Blogger publishing
# --------------------------------------------------------------------------
def get_blogger_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
        client_id=os.environ["BLOGGER_CLIENT_ID"],
        client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/blogger"],
    )
    creds.refresh(GoogleAuthRequest())
    return build("blogger", "v3", credentials=creds)


SOURCE_LABELS = {
    "facebook": "فيسبوك",
    "instagram": "إنستغرام",
    "tiktok": "تيك توك",
}


def build_post_html(item):
    label = SOURCE_LABELS.get(item["source"], item["source"])
    parts = []
    if item.get("image_url"):
        parts.append(
            f'<img src="{html.escape(item["image_url"])}" alt="{html.escape(item["title"])}" '
            f'style="max-width:100%;height:auto;border-radius:8px;margin-bottom:12px;">'
        )
    if item.get("body_html"):
        parts.append(item["body_html"])
    if item.get("permalink"):
        parts.append(
            f'<p style="margin-top:16px;font-size:0.9em;color:#666;">'
            f'🔗 المصدر الأصلي: <a href="{html.escape(item["permalink"])}" target="_blank" rel="noopener">'
            f'عرض المنشور على {label}</a></p>'
        )
    parts.append(
        f'<p style="font-size:0.8em;color:#999;">تم النشر تلقائياً عبر نظام الأتمتة — '
        f'المصدر: {label}</p>'
    )
    return "\n".join(parts)


def publish_item(service, blog_id, item):
    body = {
        "title": item["title"] or f"منشور جديد من {SOURCE_LABELS.get(item['source'], item['source'])}",
        "content": build_post_html(item),
    }
    result = service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()
    return result.get("url")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    state = load_state()

    all_items = []
    all_items += fetch_facebook_posts()
    all_items += fetch_instagram_posts()
    all_items += fetch_tiktok_videos()

    new_items = [
        item for item in all_items if item["id"] not in state.get(item["source"], [])
    ]

    if not new_items:
        print("لا توجد منشورات جديدة للنشر. (No new posts to publish.)")
        return

    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    if not blog_id:
        print("[error] BLOGGER_BLOG_ID missing, cannot publish. Exiting.")
        sys.exit(1)

    service = get_blogger_service()

    generate_video = os.environ.get("GENERATE_PROMO_VIDEO", "false").lower() == "true"

    published_count = 0
    for item in sorted(new_items, key=lambda i: i.get("published_at") or ""):
        try:
            raw_text = html.unescape(
                item.get("body_html", "").replace("<p>", "").replace("</p>", "\n")
            ).strip()

            item = rewrite_item_with_claude(item)
            url = publish_item(service, blog_id, item)
            print(f"[ok] نُشر: {item['title']}  ->  {url}")
            state.setdefault(item["source"], []).append(item["id"])
            published_count += 1

            send_whatsapp_notification(item["title"], url)

            if item["source"] == "facebook":
                maybe_update_listings_page(service, raw_text, item)

            if generate_video and item.get("image_url"):
                try:
                    import make_promo_video

                    make_promo_video.create_and_publish_promo_video(item, blog_url=url)
                except Exception as exc:  # noqa: BLE001
                    print(f"[promo-video] فشل إنشاء/نشر الفيديو الترويجي — {exc}")

        except Exception as exc:  # noqa: BLE001
            print(f"[error] فشل نشر {item['source']}:{item['id']} — {exc}")

    save_state(state)
    print(f"تم نشر {published_count} منشور(ات) جديد(ة).")


if __name__ == "__main__":
    main()
