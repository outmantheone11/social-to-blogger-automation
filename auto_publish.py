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

NOTE: GitHub Actions passes secrets/variables that were never defined as
EMPTY strings (not as "unset"). Every optional setting below therefore treats
an empty value exactly like a missing one and falls back to its default.

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
  GRAPH_API_VERSION     default "v25.0"
  SKIP_REMEMBER         "true" to remember (and never retry) items rejected
                        by the publishability check

  # Feature: auto-insert new Facebook listings into the "عروض مختارة"
  # section of the landing page (see listings_update.py). Requires
  # ANTHROPIC_API_KEY too (used to classify/extract the listing fields).
  # Leave BLOGGER_PAGE_ID unset to skip this feature entirely.
  BLOGGER_PAGE_ID       the numeric Page ID of the landing page (NOT the
                        blog ID) — find it via pages().list(blogId=...)

  # Feature: Claude-powered rewrite into a polished blog-post style.
  # Leave ANTHROPIC_API_KEY unset to skip this step (original text is used as-is).
  ANTHROPIC_API_KEY
  ANTHROPIC_MODEL           default "claude-sonnet-5-5"

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
import re
import sys
import json
import html
import datetime
import pathlib

import requests

# Arabic output must never crash the script on a runner with a non-UTF-8 locale.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------
# Environment helpers
# --------------------------------------------------------------------------
def _env(name, default=""):
    """Like os.environ.get, but an empty/blank value counts as missing.
    (GitHub Actions turns an undefined `${{ secrets.X }}` / `${{ vars.X }}`
    into "", which os.environ.get would happily return instead of default.)"""
    value = os.environ.get(name)
    if value is not None and value.strip():
        return value.strip()
    return default


def _env_int(name, default):
    raw = _env(name, str(default))
    try:
        return int(raw)
    except ValueError:
        print(f"[warn] {name}={raw!r} ليست رقماً صحيحاً، سيُستخدم {default}")
        return default


MAX_ITEMS_PER_SOURCE = _env_int("MAX_ITEMS_PER_SOURCE", 5)
STATE_FILE = pathlib.Path(_env("STATE_FILE", "state/published_ids.json"))
GRAPH_API_VERSION = _env("GRAPH_API_VERSION", "v25.0")
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5-5"
MAX_STATE_IDS_PER_SOURCE = 500  # dedup only needs the recent window; stop unbounded growth

SOURCES = ("facebook", "instagram", "tiktok")

_TOKEN_RE = re.compile(r"(access_token|token|secret)=[^&\s'\"]+", re.I)


def _safe_exc(exc):
    """Exception text with any token query-parameters redacted."""
    redacted = _TOKEN_RE.sub(r"\1=***", str(exc))
    return f"{type(exc).__name__}: {redacted}"


def _anthropic_model():
    return _env("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)


def _request_json(method, url, source, **kwargs):
    """Perform an HTTP request and return the decoded JSON body, or None on
    any network/HTTP/JSON problem. Never raises, so one broken source can't
    abort the other sources."""
    try:
        resp = requests.request(method, url, timeout=30, **kwargs)
    except requests.RequestException as exc:
        print(f"[{source}] network error — {_safe_exc(exc)}")
        return None
    if resp.status_code != 200:
        print(f"[{source}] API error {resp.status_code}: {resp.text[:300]}")
        return None
    try:
        data = resp.json()
    except ValueError:
        print(f"[{source}] رد غير صالح (ليس JSON): {resp.text[:200]}")
        return None
    return data if isinstance(data, dict) else None


# --------------------------------------------------------------------------
# State (de-duplication)
# --------------------------------------------------------------------------
def load_state():
    """Load the dedup state. A corrupt file aborts the run: starting "fresh"
    would re-publish the latest posts of every source as duplicates."""
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(
                f"[error] ملف الحالة {STATE_FILE} تالف أو غير مقروء ({_safe_exc(exc)}). "
                "تم الإيقاف لتفادي النشر المكرر — أصلح الملف أو احذفه ثم أعد التشغيل."
            )
            sys.exit(1)
        if not isinstance(state, dict):
            print(f"[error] ملف الحالة {STATE_FILE} له بنية غير متوقعة. تم الإيقاف.")
            sys.exit(1)
    for source in SOURCES:
        if not isinstance(state.get(source), list):
            state[source] = []
    return state


def save_state(state):
    trimmed = {
        key: (value[-MAX_STATE_IDS_PER_SOURCE:] if isinstance(value, list) else value)
        for key, value in state.items()
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _remember(state, item):
    ids = state.setdefault(item["source"], [])
    if item["id"] not in ids:
        ids.append(item["id"])


# --------------------------------------------------------------------------
# Fetchers — each returns a list of dicts: id, title, body_html, permalink,
# image_url, published_at (ISO string)
# --------------------------------------------------------------------------
def fetch_facebook_posts():
    page_id = _env("FB_PAGE_ID")
    token = _env("FB_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        print("[facebook] skipped (no credentials)")
        return []

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/posts"
    params = {
        "fields": "id,message,created_time,permalink_url,full_picture",
        "limit": MAX_ITEMS_PER_SOURCE,
        "access_token": token,
    }
    data = _request_json("GET", url, "facebook", params=params)
    if data is None:
        return []

    items = []
    for post in data.get("data", []):
        message = post.get("message")
        if not post.get("id") or not message:
            continue  # skip posts with no text (e.g. pure link shares with no caption)
        items.append(
            {
                "source": "facebook",
                "id": post["id"],
                "title": (message.strip().split("\n")[0])[:80],
                "body_html": _text_to_html(message),
                "permalink": post.get("permalink_url", ""),
                "image_url": post.get("full_picture"),
                "published_at": post.get("created_time"),
            }
        )
    return items


def fetch_instagram_posts():
    ig_user_id = _env("IG_USER_ID")
    token = _env("IG_ACCESS_TOKEN")
    if not ig_user_id or not token:
        print("[instagram] skipped (no credentials)")
        return []

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media"
    params = {
        "fields": "id,caption,permalink,media_url,thumbnail_url,media_type,timestamp",
        "limit": MAX_ITEMS_PER_SOURCE,
        "access_token": token,
    }
    data = _request_json("GET", url, "instagram", params=params)
    if data is None:
        return []

    items = []
    for media in data.get("data", []):
        if not media.get("id"):
            continue
        caption = media.get("caption") or ""
        # For VIDEO/REELS, media_url is the .mp4 — not usable as an <img>.
        # The still frame lives in thumbnail_url.
        if media.get("media_type") == "VIDEO":
            image_url = media.get("thumbnail_url")
        else:
            image_url = media.get("media_url")
        items.append(
            {
                "source": "instagram",
                "id": media["id"],
                "title": (caption.strip().split("\n")[0] if caption.strip() else "منشور إنستغرام جديد")[:80],
                "body_html": _text_to_html(caption) if caption.strip() else "",
                "permalink": media.get("permalink", ""),
                "image_url": image_url,
                "published_at": media.get("timestamp"),
            }
        )
    return items


def fetch_tiktok_videos():
    token = _env("TIKTOK_ACCESS_TOKEN")
    open_id = _env("TIKTOK_OPEN_ID")
    if not token or not open_id:
        print("[tiktok] skipped (no credentials)")
        return []

    # TikTok "Content Posting API" / "Display API" — video.list endpoint.
    # NOTE: TikTok's public API only exposes videos belonging to the
    # authenticated/own account; there is no supported way to pull videos
    # from third-party accounts.
    url = "https://open.tiktokapis.com/v2/video/list/"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"max_count": MAX_ITEMS_PER_SOURCE}
    fields = "id,title,video_description,share_url,cover_image_url,create_time"
    payload = _request_json("POST", f"{url}?fields={fields}", "tiktok", headers=headers, json=body)
    if payload is None:
        return []

    data = payload.get("data") or {}
    items = []
    for video in data.get("videos") or []:
        if not video.get("id"):
            continue  # str(None) would otherwise become the bogus id "None"
        desc = video.get("video_description") or video.get("title") or "فيديو تيكتوك جديد"
        create_ts = video.get("create_time")
        published_at = None
        if create_ts:
            try:
                published_at = datetime.datetime.fromtimestamp(
                    int(create_ts), tz=datetime.timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
            except (TypeError, ValueError, OverflowError, OSError):
                published_at = None
        items.append(
            {
                "source": "tiktok",
                "id": str(video["id"]),
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


def _parse_timestamp(value):
    """Parse the different ISO formats the three APIs return ("...+0000",
    "...Z", ...) into an aware datetime so the oldest-first ordering is
    correct. Unparseable/missing values sort first."""
    fallback = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    if not value:
        return fallback
    text = str(value).strip().replace("Z", "+00:00")
    text = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", text)
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def _sort_key(item):
    return _parse_timestamp(item.get("published_at"))


# --------------------------------------------------------------------------
# Claude helpers
# --------------------------------------------------------------------------
def _response_text(response):
    return "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()


def _strip_markdown(line, is_title=False):
    line = re.sub(r"^\s*#+\s*", "", line)          # "## heading"
    line = re.sub(r"^\s*>\s*", "", line)           # "> quote"
    if is_title:
        line = re.sub(r"^\s*[-*•]\s+", "", line)   # bullet before a title
    line = re.sub(r"(\*\*|__|`)", "", line)        # bold / code markers
    return line.strip()


def _parse_json_object(text):
    """Parse a JSON object from a model reply, tolerating ```json fences or
    short surrounding text. Raises ValueError/JSONDecodeError otherwise."""
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S | re.I)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("الرد ليس كائن JSON")
    return data


# --------------------------------------------------------------------------
# Feature: rewrite the raw social caption into a polished blog-post style
# using the Anthropic API. Fully optional — if ANTHROPIC_API_KEY is not set,
# this is skipped and the original text passes through unchanged.
# --------------------------------------------------------------------------
def rewrite_item_with_claude(item):
    api_key = _env("ANTHROPIC_API_KEY")
    raw_text = html.unescape(
        item.get("body_html", "").replace("<p>", "").replace("</p>", "\n")
    ).strip()
    if not api_key or not raw_text:
        return item  # unchanged

    try:
        import anthropic  # imported lazily so the package is only required when used

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "أعد صياغة النص التالي، المأخوذ من منشور على وسائل التواصل الاجتماعي، "
            "ليصبح مقالاً قصيراً بأسلوب مدونة احترافي وسلس بالعربية الفصحى، مع عنوان "
            "جذاب في أول سطر. حافظ على المعنى والمعلومات الأساسية ولا تضف معلومات غير "
            "موجودة في النص الأصلي. أعد فقط النص المُعاد صياغته بدون أي تعليق إضافي.\n\n"
            f"النص الأصلي:\n{raw_text}"
        )
        response = client.messages.create(
            model=_anthropic_model(),
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        rewritten = _response_text(response)
        if not rewritten:
            return item

        lines = [line for line in rewritten.split("\n") if line.strip()]
        if not lines:
            return item
        new_title = _strip_markdown(lines[0], is_title=True)[:80] or item["title"]
        body_lines = [_strip_markdown(line) for line in lines[1:]]
        body_lines = [line for line in body_lines if line]
        new_body = "\n".join(f"<p>{html.escape(line)}</p>" for line in body_lines) or item.get(
            "body_html", ""
        )
        item = dict(item)  # don't mutate the caller's dict in place
        item["title"] = new_title
        item["body_html"] = new_body
        item["rewritten"] = True
    except Exception as exc:  # noqa: BLE001
        print(f"[claude-rewrite] فشل إعادة الصياغة، سيُنشر النص الأصلي — {_safe_exc(exc)}")
    return item


# --------------------------------------------------------------------------
# Feature: WhatsApp notification to yourself for every newly published post.
# Fully optional — skipped silently if the WhatsApp env vars are not set.
# --------------------------------------------------------------------------
def send_whatsapp_notification(title, url):
    phone_number_id = _env("WHATSAPP_PHONE_NUMBER_ID")
    token = _env("WHATSAPP_ACCESS_TOKEN")
    to_number = _env("WHATSAPP_TO_NUMBER")
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
        print(f"[whatsapp] فشل إرسال الإشعار — {_safe_exc(exc)}")


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
    api_key = _env("ANTHROPIC_API_KEY")
    page_id = _env("BLOGGER_PAGE_ID")
    if not api_key or not page_id or not raw_text.strip():
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_anthropic_model(),
            max_tokens=500,
            system=LISTING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": raw_text}],
        )
        data = _parse_json_object(_response_text(response))
        if not data.get("is_listing"):
            return None
        return data
    except Exception as exc:  # noqa: BLE001
        print(f"[listing-classify] فشل تحليل المنشور كعقار، سيُتجاهل — {_safe_exc(exc)}")
        return None


def maybe_update_listings_page(service, raw_text, item):
    """If configured and the post is a property listing, insert it into the
    LISTINGS array on the landing page. Never raises — logs and continues."""
    blog_id = _env("BLOGGER_BLOG_ID")
    page_id = _env("BLOGGER_PAGE_ID")
    if not blog_id or not page_id:
        return  # feature not configured, skip silently

    listing = classify_listing_with_claude(raw_text)
    if not listing:
        return

    if item.get("image_url"):
        listing["image_url"] = item["image_url"]

    try:
        import listings_update  # lazy: this optional feature must not break the main flow

        inserted = listings_update.insert_listing(service, blog_id, page_id, listing)
        if inserted:
            print(f"[listings] أُضيف عرض جديد إلى صفحة العقارات: {listing.get('title', '')}")
        else:
            print("[listings] العرض موجود مسبقاً في الصفحة، تم تجاهله.")
    except Exception as exc:  # noqa: BLE001
        print(f"[listings] فشل تحديث صفحة العقارات — {_safe_exc(exc)}")


# --------------------------------------------------------------------------
# Blogger publishing
# --------------------------------------------------------------------------
def get_blogger_service():
    missing = [
        name
        for name in ("BLOGGER_REFRESH_TOKEN", "BLOGGER_CLIENT_ID", "BLOGGER_CLIENT_SECRET")
        if not _env(name)
    ]
    if missing:
        print(f"[error] متغيرات Blogger المطلوبة مفقودة: {', '.join(missing)}. Exiting.")
        sys.exit(1)

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=_env("BLOGGER_REFRESH_TOKEN"),
        client_id=_env("BLOGGER_CLIENT_ID"),
        client_secret=_env("BLOGGER_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/blogger"],
    )
    try:
        creds.refresh(GoogleAuthRequest())
    except Exception as exc:  # noqa: BLE001
        print(f"[error] فشل تجديد رمز Blogger (هل انتهت صلاحية refresh token؟) — {_safe_exc(exc)}")
        sys.exit(1)
    return build("blogger", "v3", credentials=creds, cache_discovery=False)


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


GENERIC_TITLE_RE = re.compile(r"^\s*منشور\s+(من|جديد\s+من)\s*\S*\s*$", re.I)


def is_publishable(item):
    """يرفض العناصر الفارغة أو ذات العنوان العام، لأنها تعني فشل الجلب."""
    body = html.unescape(item.get("body_html", "") or "")
    text = re.sub(r"<[^>]+>", " ", body).strip()
    has_media = bool(item.get("image_url") or item.get("video_url") or item.get("media_urls"))
    title = (item.get("title") or "").strip()
    if GENERIC_TITLE_RE.match(title):
        return False, "عنوان عام"
    if len(text) < 30 and not has_media:
        return False, "نص قصير بلا وسائط"
    return True, ""


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

    blog_id = _env("BLOGGER_BLOG_ID")
    if not blog_id:
        print("[error] BLOGGER_BLOG_ID missing, cannot publish. Exiting.")
        sys.exit(1)

    service = get_blogger_service()

    generate_video = _env("GENERATE_PROMO_VIDEO", "false").lower() == "true"
    skip_remember = _env("SKIP_REMEMBER", "false").lower() == "true"

    published_count = 0
    failed_count = 0
    for item in sorted(new_items, key=_sort_key):
        try:
            raw_text = html.unescape(
                item.get("body_html", "").replace("<p>", "").replace("</p>", "\n")
            ).strip()

            ok, why = is_publishable(item)
            if not ok:
                print(f"[skip] {item['source']}:{item['id']} — {why}")
                if skip_remember:
                    _remember(state, item)
                    save_state(state)
                continue

            item = rewrite_item_with_claude(item)
            ok, why = is_publishable(item)
            if not ok:
                print(f"[skip] بعد إعادة الصياغة {item['source']}:{item['id']} — {why}")
                continue

            url = publish_item(service, blog_id, item)
        except Exception as exc:  # noqa: BLE001
            failed_count += 1
            print(f"[error] فشل نشر {item['source']}:{item['id']} — {_safe_exc(exc)}")
            continue

        print(f"[ok] نُشر: {item['title']}  ->  {url}")
        published_count += 1
        # Persist right away: the post is already live, so a crash further down
        # (or a failed workflow step) must not cause it to be published twice.
        _remember(state, item)
        save_state(state)

        # Extras after a successful publish never affect the result above.
        send_whatsapp_notification(item["title"], url)

        if item["source"] == "facebook":
            maybe_update_listings_page(service, raw_text, item)

        if generate_video and item.get("image_url"):
            try:
                import make_promo_video

                make_promo_video.create_and_publish_promo_video(item, blog_url=url)
            except Exception as exc:  # noqa: BLE001
                print(f"[promo-video] فشل إنشاء/نشر الفيديو الترويجي — {_safe_exc(exc)}")

    print(f"تم نشر {published_count} منشور(ات) جديد(ة).")
    if failed_count and not published_count:
        print(f"[error] فشل نشر جميع المنشورات المحاولة ({failed_count}).")
        sys.exit(1)


if __name__ == "__main__":
    main()
