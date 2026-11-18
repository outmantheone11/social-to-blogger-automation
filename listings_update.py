#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
listings_update.py
--------------------
Inserts new real-estate / land listings into the `var LISTINGS = [...]`
JavaScript array embedded inside a specific Blogger Page (the landing page
at BLOGGER_PAGE_ID — e.g. "منصة الوساطة العقارية والتجارية"), without
touching anything else on the page (hero section, calculator, testimonials,
footer, etc.).

This is NOT a normal Blogger blog post. It is a single static Page whose
"عروض مختارة" (Featured offers) section is rendered client-side by reading
the LISTINGS array. The filter buttons on that page use:
    data-filter="all" | "land" | "residential"
and the card-rendering JS reads `item.category` to decide which filter
group a card belongs to, and `item.media` to pick a CSS style class
("is-res", "is-land", "is-coast", ...) for the card's media area.

Each listing object looks like this (unquoted keys, double-quoted string
values — this is hand-authored JS, not JSON):

    {
      category:"land", badge:"للبيع · أرض استثمارية", media:"land",
      title:"...", location:"...", area:"...", price:"...",
      wa:"..."
    }

`image_url` and `video_url` are OPTIONAL keys — omit them entirely when
there is nothing to show (do not emit empty-string keys; the existing data
mixes both styles, but omitting is cleaner and what most items already do).

Required environment variables (same ones auto_publish.py already uses):
  BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET,
  BLOGGER_REFRESH_TOKEN
  BLOGGER_PAGE_ID   the numeric Page ID of the landing page (NOT the blog ID;
                     find it with: pages().list(blogId=...) and match the URL)
"""

import os
import re
import json

VALID_CATEGORIES = {"residential", "land"}
VALID_MEDIA = {"res", "land", "coast"}

ARRAY_START_MARKER = "var LISTINGS"
ITEM_INDENT = "    "   # 4 spaces before "{" / "}"
FIELD_INDENT = "      "  # 6 spaces before each field


def _js_string(value):
    """Escape a Python string for embedding as a double-quoted JS string
    literal, matching the style already used on the page."""
    value = "" if value is None else str(value)
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    value = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return '"' + value.strip() + '"'


def format_listing_js(item):
    """Render one listing dict as a JS object literal matching the exact
    style used in the live page (unquoted keys, grouped fields, 4/6-space
    indent). Raises ValueError if required fields are missing/invalid."""
    category = item.get("category")
    media = item.get("media")
    if category not in VALID_CATEGORIES:
        raise ValueError(f"category غير صالحة: {category!r} (يجب أن تكون residential أو land)")
    if media not in VALID_MEDIA:
        raise ValueError(f"media غير صالحة: {media!r} (يجب أن تكون res أو land أو coast)")
    for required in ("badge", "title", "location", "area", "price", "wa"):
        if not item.get(required):
            raise ValueError(f"الحقل المطلوب '{required}' مفقود أو فارغ")

    lines = [ITEM_INDENT + "{"]
    lines.append(
        f"{FIELD_INDENT}category:{_js_string(category)}, "
        f"badge:{_js_string(item['badge'])}, media:{_js_string(media)},"
    )
    lines.append(f"{FIELD_INDENT}title:{_js_string(item['title'])},")
    lines.append(
        f"{FIELD_INDENT}location:{_js_string(item['location'])}, "
        f"area:{_js_string(item['area'])}, price:{_js_string(item['price'])},"
    )
    extra = []
    if item.get("image_url"):
        extra.append(f"image_url:{_js_string(item['image_url'])}")
    if item.get("video_url"):
        extra.append(f"video_url:{_js_string(item['video_url'])}")
    if extra:
        lines.append(FIELD_INDENT + ", ".join(extra) + ",")
    lines.append(f"{FIELD_INDENT}wa:{_js_string(item['wa'])}")
    lines.append(ITEM_INDENT + "}")
    return "\n".join(lines)


def _find_array_bounds(html):
    """Return (array_start, insert_point, array_end) character offsets.
    array_start = index of 'var LISTINGS'
    insert_point = index right after the array's opening '['
    array_end = index right after the closing '];'
    Raises ValueError if the marker/structure isn't found (never touches
    the page in that case)."""
    start = html.find(ARRAY_START_MARKER)
    if start == -1:
        raise ValueError("لم يتم العثور على 'var LISTINGS' في محتوى الصفحة.")

    bracket_open = html.find("[", start)
    if bracket_open == -1:
        raise ValueError("تعذّر إيجاد '[' بعد 'var LISTINGS'.")

    end = html.find("];", bracket_open)
    if end == -1:
        raise ValueError("تعذّر إيجاد نهاية المصفوفة '];'.")

    return start, bracket_open + 1, end + 2


def insert_listing_into_html(html, item):
    """Pure function: returns a NEW html string with `item` inserted as the
    first element of the LISTINGS array. Does not touch Blogger."""
    item_js = format_listing_js(item)
    _, insert_point, _ = _find_array_bounds(html)

    before = html[:insert_point]
    after = html[insert_point:]

    # Insert as the newest/first item. after currently starts right past
    # "[" — typically "\n    {\n ..." for an existing non-empty array, or
    # "\n  ];" for an empty one. Either way, inject "\n" + item + "," first.
    new_html = before + "\n" + item_js + "," + after
    return new_html


def listing_already_present(html, wa_text):
    """Best-effort duplicate guard: checks whether a listing with this
    exact `wa` message already exists in the array (used as the closest
    thing to a stable identifier, since listings don't carry a source ID)."""
    _, insert_point, array_end = _find_array_bounds(html)
    array_body = html[insert_point:array_end]
    return _js_string(wa_text) in array_body


def insert_listing(service, blog_id, page_id, item):
    """Fetch the page, insert `item` into LISTINGS, and write it back.
    Returns True if inserted, False if skipped as a likely duplicate.
    Raises on any structural problem rather than risking a broken page."""
    page = service.pages().get(blogId=blog_id, pageId=page_id, view="ADMIN").execute()
    html = page["content"]

    if listing_already_present(html, item.get("wa", "")):
        return False

    new_html = insert_listing_into_html(html, item)

    # Sanity check: the edit must be a pure insertion — same page length
    # plus roughly the inserted block, and the LISTINGS marker must still
    # be found at the same offset. This catches any marker/regex drift
    # before it reaches the live site.
    if ARRAY_START_MARKER not in new_html:
        raise ValueError("فحص الأمان فشل: اختفى 'var LISTINGS' بعد التعديل — تم إلغاء التحديث.")

    service.pages().update(
        blogId=blog_id, pageId=page_id, body={"content": new_html}
    ).execute()
    return True
