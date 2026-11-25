#!/usr/bin/env python3
"""Publish an offer approved by the wassata agent (repository_dispatch event: new-offer).

  render   build the poster image from the offer HTML -> media/offers/<offer_id>.jpg
  publish  post it to the Blogger listings page, the Facebook page and Instagram.
           Each platform is independent: a failure in one does not stop the others.
           Already-published offers are skipped (state/published_offers.json).
"""
import json
import os
import pathlib
import sys

import requests

STATE_FILE = pathlib.Path("state/published_offers.json")
MEDIA_DIR = pathlib.Path("media/offers")
GRAPH = "https://graph.facebook.com/v21.0"
BLOG_PAGE_ID = os.environ.get("BLOGGER_PAGE_ID", "2288061485082308217")


def load_payload() -> dict:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        sys.exit("GITHUB_EVENT_PATH is missing: run this from GitHub Actions")
    with open(path, encoding="utf-8") as f:
        event = json.load(f)
    payload = event.get("client_payload") or {}
    if "offer_id" not in payload:
        sys.exit("this run was not triggered by a wassata offer (no client_payload.offer_id)")
    return payload


def image_path(payload: dict) -> pathlib.Path:
    return MEDIA_DIR / f"{payload['offer_id']}.jpg"


def image_url(payload: dict) -> str:
    repo = os.environ["GITHUB_REPOSITORY"]
    ref = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{image_path(payload).as_posix()}"


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def render(payload: dict) -> None:
    from playwright.sync_api import sync_playwright

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.set_content(payload["poster_html"], wait_until="load")
        page.screenshot(path=str(image_path(payload)), type="jpeg", quality=92)
        browser.close()
    print("poster rendered:", image_path(payload))


def publish_blogger(payload: dict, url: str) -> bool:
    from auto_publish import get_blogger_service
    from listings_update import insert_listing

    item = {
        "category": payload["category"],
        "media": payload["media"],
        "badge": payload["badge"],
        "title": payload["title"],
        "location": payload["location"],
        "area": payload["area"],
        "price": payload["price"],
        "image_url": url,
        "wa": f"مرحباً، أرغب في تفاصيل العرض رقم {payload['offer_id']}: {payload['title']}",
    }
    return insert_listing(get_blogger_service(), os.environ["BLOGGER_BLOG_ID"], BLOG_PAGE_ID, item)


def publish_facebook(payload: dict, url: str) -> str:
    r = requests.post(
        f"{GRAPH}/{os.environ['FB_PAGE_ID']}/photos",
        data={"url": url, "caption": payload["caption"], "access_token": os.environ["FB_PAGE_ACCESS_TOKEN"]},
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("id", "")


def publish_instagram(payload: dict, url: str) -> str:
    ig = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    container = requests.post(
        f"{GRAPH}/{ig}/media",
        data={"image_url": url, "caption": payload["caption"], "access_token": token},
        timeout=60,
    )
    container.raise_for_status()
    published = requests.post(
        f"{GRAPH}/{ig}/media_publish",
        data={"creation_id": container.json()["id"], "access_token": token},
        timeout=60,
    )
    published.raise_for_status()
    return published.json().get("id", "")


def publish(payload: dict) -> None:
    key = str(payload["offer_id"])
    state = load_state()
    if key in state:
        print(f"offer {key} already published, skipping")
        return
    url = image_url(payload)
    result = {}
    targets = (
        ("blogger", lambda: publish_blogger(payload, url)),
        ("facebook", lambda: publish_facebook(payload, url)),
        ("instagram", lambda: publish_instagram(payload, url)),
    )
    for name, action in targets:
        try:
            result[name] = action()
            print(f"{name}: ok")
        except Exception as exc:  # noqa: BLE001  - one platform must not stop the others
            result[name] = f"error: {exc}"
            print(f"{name} failed: {exc}")
    state[key] = result
    save_state(state)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    data = load_payload()
    if command == "render":
        render(data)
    elif command == "publish":
        publish(data)
    else:
        sys.exit("usage: new_offer.py render|publish")
