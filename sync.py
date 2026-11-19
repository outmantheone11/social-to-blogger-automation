#!/usr/bin/env python3
"""Facebook + Instagram + YouTube  ->  Blogger

Usage:
    python sync.py fetch      # fetch new items, download images, save to pending.json
    python sync.py publish    # publish pending items to Blogger
    python sync.py            # fetch + publish
    python sync.py --dry-run  # only print what would be fetched

Only the Python standard library is used (no pip install needed).
"""
import hashlib
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GRAPH = "https://graph.facebook.com/v21.0"
STATE_FILE = Path(os.getenv("STATE_FILE", "state.json"))
PENDING_FILE = Path(os.getenv("PENDING_FILE", "pending.json"))
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "media"))
LIMIT = int(os.getenv("LIMIT", "5"))  # items per source per run
DRAFT = os.getenv("BLOGGER_DRAFT", "1") == "1"  # 1 = save as draft (safe default)
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "").rstrip("/")
DRY_RUN = "--dry-run" in sys.argv


class Skip(Exception):
    """Source skipped (missing config)."""


def env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise Skip(f"missing env var {name}")
    return value


def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        # never print the query string: it contains tokens
        raise RuntimeError(f"HTTP {e.code} {url.split('?')[0]}: {body[:500]}")


def get_json(url, params):
    return json.loads(http(url + "?" + urllib.parse.urlencode(params)))


def load(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------
# Sources. Each returns a list of items:
# {uid, source, title, text, date, link, images: [url], embeds: [[url, height]]}
# --------------------------------------------------------------------------

def fetch_facebook():
    token, page = env("FB_PAGE_TOKEN"), env("FB_PAGE_ID")
    fields = (
        "id,message,created_time,permalink_url,full_picture,"
        "attachments{media_type,media,url,subattachments{media_type,media,url}}"
    )
    data = get_json(f"{GRAPH}/{page}/posts",
                    {"fields": fields, "limit": LIMIT, "access_token": token})
    items = []
    for p in data.get("data", []):
        images, embeds = [], []
        for att in p.get("attachments", {}).get("data", []):
            subs = att.get("subattachments", {}).get("data") or [att]
            for s in subs:
                kind = s.get("media_type")
                if kind == "photo":
                    src = s.get("media", {}).get("image", {}).get("src")
                    if src:
                        images.append(src)
                elif kind == "video":
                    href = s.get("url") or p.get("permalink_url")
                    if href:
                        embeds.append([
                            "https://www.facebook.com/plugins/video.php?href="
                            + urllib.parse.quote(href, safe="") + "&show_text=false&width=560",
                            315])
        if not images and not embeds and p.get("full_picture"):
            images.append(p["full_picture"])
        text = p.get("message", "")
        if not (text or images or embeds):
            continue
        items.append({
            "uid": "fb:" + p["id"], "source": "Facebook", "title": "",
            "text": text, "date": p.get("created_time", ""),
            "link": p.get("permalink_url", ""), "images": images, "embeds": embeds,
        })
    return items


def instagram_user_id():
    if os.getenv("IG_USER_ID", "").strip():
        return os.environ["IG_USER_ID"].strip()
    token, page = env("FB_PAGE_TOKEN"), env("FB_PAGE_ID")
    d = get_json(f"{GRAPH}/{page}", {"fields": "instagram_business_account",
                                    "access_token": token})
    ig = d.get("instagram_business_account", {}).get("id")
    if not ig:
        raise Skip("no Instagram business account linked to the page")
    return ig


def fetch_instagram():
    token = env("FB_PAGE_TOKEN")
    ig = instagram_user_id()
    fields = ("id,caption,media_type,media_url,permalink,timestamp,"
              "children{media_type,media_url}")
    data = get_json(f"{GRAPH}/{ig}/media",
                    {"fields": fields, "limit": LIMIT, "access_token": token})
    items = []
    for m in data.get("data", []):
        images, embeds = [], []
        embed_url = m.get("permalink", "").rstrip("/") + "/embed"
        kind = m.get("media_type")
        if kind == "IMAGE" and m.get("media_url"):
            images.append(m["media_url"])
        elif kind == "VIDEO":  # includes reels
            embeds.append([embed_url, 720])
        elif kind == "CAROUSEL_ALBUM":
            has_video = False
            for c in m.get("children", {}).get("data", []):
                if c.get("media_type") == "IMAGE" and c.get("media_url"):
                    images.append(c["media_url"])
                else:
                    has_video = True
            if has_video:
                images = []  # the embed shows the whole carousel, videos included
                embeds.append([embed_url, 720])
        items.append({
            "uid": "ig:" + m["id"], "source": "Instagram", "title": "",
            "text": m.get("caption", ""), "date": m.get("timestamp", ""),
            "link": m.get("permalink", ""), "images": images, "embeds": embeds,
        })
    return items


def fetch_youtube():
    key, channel = env("YT_API_KEY"), env("YT_CHANNEL_ID")
    d = get_json("https://www.googleapis.com/youtube/v3/channels",
                 {"part": "contentDetails", "id": channel, "key": key})
    if not d.get("items"):
        raise RuntimeError("YouTube channel not found, check YT_CHANNEL_ID")
    uploads = d["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    d = get_json("https://www.googleapis.com/youtube/v3/playlistItems",
                 {"part": "snippet", "playlistId": uploads,
                  "maxResults": LIMIT, "key": key})
    items = []
    for it in d.get("items", []):
        sn = it["snippet"]
        if sn.get("title") in ("Private video", "Deleted video"):
            continue
        vid = sn["resourceId"]["videoId"]
        items.append({
            "uid": "yt:" + vid, "source": "YouTube", "title": sn.get("title", ""),
            "text": sn.get("description", ""), "date": sn.get("publishedAt", ""),
            "link": "https://www.youtube.com/watch?v=" + vid, "images": [],
            "embeds": [["https://www.youtube.com/embed/" + vid, 315]],
        })
    return items


def collect():
    fns = {"facebook": fetch_facebook, "instagram": fetch_instagram,
           "youtube": fetch_youtube}
    wanted = [s.strip() for s in os.getenv("SOURCES", "facebook,instagram,youtube").split(",")]
    items = []
    for name in wanted:
        fn = fns.get(name)
        if not fn:
            continue
        try:
            got = fn()
            print(f"[{name}] {len(got)} items")
            items += got
        except Skip as e:
            print(f"[{name}] skipped: {e}")
        except Exception as e:  # one failing source must not stop the others
            print(f"[{name}] ERROR: {e}")
    return items


# --------------------------------------------------------------------------
# Images: Blogger API cannot upload media, so images must be hosted somewhere.
# Facebook/Instagram CDN links expire, so we download them into ./media and
# serve them through MEDIA_BASE_URL (e.g. jsDelivr over this GitHub repo).
# --------------------------------------------------------------------------

def localize_image(url):
    if not MEDIA_BASE_URL:
        return url
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + ext
    try:
        MEDIA_DIR.mkdir(exist_ok=True)
        (MEDIA_DIR / name).write_bytes(http(url))
        return f"{MEDIA_BASE_URL}/{name}"
    except Exception as e:
        print(f"  image download failed, keeping original link: {e}")
        return url


# --------------------------------------------------------------------------
# Blogger
# --------------------------------------------------------------------------

def make_title(it):
    if it.get("title"):
        return it["title"][:100]
    first = (it["text"].strip().splitlines() or [""])[0].strip()
    if first:
        return first[:80] + ("..." if len(first) > 80 else "")
    return f"منشور من {it['source']}"


def build_html(it):
    parts = ['<div dir="auto" style="line-height:1.8">']
    if it["text"]:
        parts.append("<p>" + html.escape(it["text"]).replace("\n", "<br>") + "</p>")
    for src in it["images"]:
        parts.append(f'<p><img src="{html.escape(src, quote=True)}" '
                     'style="max-width:100%;height:auto" loading="lazy"></p>')
    for url, height in it["embeds"]:
        parts.append(f'<p><iframe src="{html.escape(url, quote=True)}" width="560" '
                     f'height="{height}" style="max-width:100%;border:0" '
                     'allowfullscreen loading="lazy"></iframe></p>')
    if it["link"]:
        parts.append(f'<p><a href="{html.escape(it["link"], quote=True)}" '
                     f'rel="nofollow noopener">المصدر الأصلي ({it["source"]})</a></p>')
    parts.append("</div>")
    return "\n".join(parts)


def blogger_access_token():
    data = urllib.parse.urlencode({
        "client_id": env("GOOGLE_CLIENT_ID"),
        "client_secret": env("GOOGLE_CLIENT_SECRET"),
        "refresh_token": env("GOOGLE_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }).encode()
    return json.loads(http("https://oauth2.googleapis.com/token",
                           data=data, method="POST"))["access_token"]


def blogger_publish(token, it):
    blog = env("BLOGGER_BLOG_ID")
    url = (f"https://www.googleapis.com/blogger/v3/blogs/{blog}/posts/"
           f"?isDraft={'true' if DRAFT else 'false'}")
    body = {"kind": "blogger#post", "title": make_title(it),
            "content": build_html(it), "labels": [it["source"]]}
    http(url, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_fetch():
    state = load(STATE_FILE, {"posted": []})
    pending = load(PENDING_FILE, [])
    known = set(state["posted"]) | {p["uid"] for p in pending}
    new = sorted((i for i in collect() if i["uid"] not in known),
                 key=lambda i: i["date"])
    print(f"{len(new)} new items")
    if DRY_RUN:
        for it in new:
            print(f"- [{it['source']}] {make_title(it)} "
                  f"(images={len(it['images'])}, videos={len(it['embeds'])})")
        return
    for it in new:
        it["images"] = [localize_image(u) for u in it["images"]]
        pending.append(it)
    save(PENDING_FILE, pending)


def cmd_publish():
    state = load(STATE_FILE, {"posted": []})
    pending = load(PENDING_FILE, [])
    if not pending:
        print("nothing to publish")
        return
    token = blogger_access_token()
    for it in list(pending):
        try:
            blogger_publish(token, it)
        except Exception as e:
            print(f"FAILED {it['uid']}: {e}")
            continue
        state["posted"].append(it["uid"])
        pending.remove(it)
        save(STATE_FILE, state)
        save(PENDING_FILE, pending)
        print(f"posted {it['uid']} ({'draft' if DRAFT else 'published'})")
        time.sleep(2)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = args[0] if args else "all"
    if mode in ("fetch", "all"):
        cmd_fetch()
    if mode in ("publish", "all") and not DRY_RUN:
        cmd_publish()
