#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_promo_video.py
--------------------
Generates a short vertical (1080x1920) promo video from a published post's
image + text, uploads it as a GitHub Release asset to get a temporary public
URL (all three platforms below require a reachable URL — none accept a raw
file upload from a GitHub Actions runner directly), then publishes that video
as:
  - an Instagram Reel
  - a Facebook Page video
  - a TikTok video (via the Content Posting API, PULL_FROM_URL)

This is the most failure-prone part of the whole pipeline because each
platform's video-publishing API is multi-step and subject to app-review
restrictions (see README "الفيديو الترويجي" section). Every network call is
wrapped so that a failure on one platform does not stop the others, and does
not affect the main blog-publishing flow at all (it already succeeded before
this module is even imported).

Environment variables used (all optional — each platform is skipped
individually if its variables are missing):
  GITHUB_TOKEN, GITHUB_REPOSITORY   provided automatically by GitHub Actions
  FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN  reused from the main script
  IG_USER_ID, IG_ACCESS_TOKEN       reused from the main script
  TIKTOK_ACCESS_TOKEN               reused from the main script
  TIKTOK_PRIVACY_LEVEL              default "SELF_ONLY" (see README — public
                                     posting requires TikTok app audit)
"""

import os
import io
import time
import pathlib
import subprocess
import tempfile
import uuid

import requests
from PIL import Image, ImageDraw, ImageFont

GRAPH_API_VERSION = "v21.0"
VIDEO_WIDTH, VIDEO_HEIGHT = 1080, 1920
VIDEO_DURATION_SECONDS = 8


# --------------------------------------------------------------------------
# 1. Build the video locally with moviepy (images in, mp4 out)
# --------------------------------------------------------------------------
def _wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _make_caption_overlay(text, size=(VIDEO_WIDTH, VIDEO_HEIGHT)):
    """Renders the caption as a transparent PNG (avoids an ImageMagick
    dependency for moviepy's TextClip, which is often missing on CI runners)."""
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64
        )
    except OSError:
        font = ImageFont.load_default()

    max_text_width = size[0] - 120
    lines = _wrap_text(text, font, max_text_width, draw)[:6]  # cap to 6 lines

    line_height = 78
    block_height = line_height * len(lines) + 60
    band_top = size[1] - block_height - 140

    draw.rectangle(
        [(0, band_top), (size[0], band_top + block_height + 80)],
        fill=(0, 0, 0, 160),
    )

    y = band_top + 40
    for line in lines:
        text_width = draw.textlength(line, font=font)
        x = (size[0] - text_width) / 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height

    return overlay


def build_video(image_url, caption_text, out_path):
    """Downloads one image, applies a slow zoom (Ken Burns effect), overlays
    the caption text, and writes an mp4 to out_path. Requires moviepy+ffmpeg."""
    from moviepy.editor import ImageClip, CompositeVideoClip

    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_image_path = pathlib.Path(tmp_dir) / "source.jpg"
        source_image_path.write_bytes(resp.content)

        base_image = Image.open(source_image_path).convert("RGB")
        base_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
        img_ratio = base_image.width / base_image.height
        if img_ratio > base_ratio:
            new_height = VIDEO_HEIGHT
            new_width = int(new_height * img_ratio)
        else:
            new_width = VIDEO_WIDTH
            new_height = int(new_width / img_ratio)
        base_image = base_image.resize((new_width, new_height))

        left = (new_width - VIDEO_WIDTH) // 2
        top = (new_height - VIDEO_HEIGHT) // 2
        base_image = base_image.crop((left, top, left + VIDEO_WIDTH, top + VIDEO_HEIGHT))

        fitted_image_path = pathlib.Path(tmp_dir) / "fitted.jpg"
        base_image.save(fitted_image_path)

        overlay_image_path = pathlib.Path(tmp_dir) / "overlay.png"
        _make_caption_overlay(caption_text).save(overlay_image_path)

        image_clip = (
            ImageClip(str(fitted_image_path))
            .set_duration(VIDEO_DURATION_SECONDS)
            .resize(lambda t: 1 + 0.04 * t)  # slow Ken-Burns zoom-in
            .set_position("center")
        )
        overlay_clip = ImageClip(str(overlay_image_path)).set_duration(
            VIDEO_DURATION_SECONDS
        )

        final = CompositeVideoClip(
            [image_clip, overlay_clip], size=(VIDEO_WIDTH, VIDEO_HEIGHT)
        )
        final.write_videofile(
            str(out_path),
            fps=30,
            codec="libx264",
            audio=False,
            preset="medium",
            threads=2,
            logger=None,
        )
    return out_path


# --------------------------------------------------------------------------
# 2. Host the video somewhere with a public URL — a GitHub Release asset is
#    the simplest option that needs no extra cloud account/secret, since the
#    workflow already runs inside the repo with a GITHUB_TOKEN.
# --------------------------------------------------------------------------
def upload_as_github_release_asset(video_path):
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise RuntimeError("GITHUB_REPOSITORY غير متوفر — هذه الميزة تعمل فقط داخل GitHub Actions")

    tag = f"promo-video-{uuid.uuid4().hex[:10]}"
    subprocess.run(
        ["gh", "release", "create", tag, str(video_path), "--repo", repo,
         "--title", tag, "--notes", "Auto-generated promo video asset."],
        check=True,
    )
    result = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo, "--json", "assets"],
        check=True, capture_output=True, text=True,
    )
    import json as _json

    assets = _json.loads(result.stdout)["assets"]
    if not assets:
        raise RuntimeError("تعذّر الحصول على رابط الفيديو بعد رفعه كـ Release asset")
    return assets[0]["url"]


# --------------------------------------------------------------------------
# 3. Publish to each platform. Each function is self-contained and never
#    raises past its own try/except — a failure here must never roll back
#    the blog post that was already published successfully.
# --------------------------------------------------------------------------
def publish_instagram_reel(video_url, caption):
    ig_user_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not (ig_user_id and token):
        print("[ig-reel] skipped (no credentials)")
        return

    create_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media"
    resp = requests.post(
        create_url,
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": token,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"[ig-reel] فشل إنشاء الحاوية: {resp.status_code} {resp.text[:300]}")
        return
    creation_id = resp.json().get("id")

    status_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"
    for _ in range(20):  # up to ~3 minutes of polling while TikTok/IG transcode the video
        status_resp = requests.get(
            status_url, params={"fields": "status_code", "access_token": token}, timeout=20
        )
        status_code = status_resp.json().get("status_code")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            print("[ig-reel] فشلت المعالجة على خوادم إنستغرام")
            return
        time.sleep(10)

    publish_resp = requests.post(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    if publish_resp.status_code == 200:
        print("[ig-reel] تم نشر الـ Reel بنجاح.")
    else:
        print(f"[ig-reel] فشل النشر النهائي: {publish_resp.status_code} {publish_resp.text[:300]}")


def publish_facebook_video(video_url, caption):
    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    if not (page_id and token):
        print("[fb-video] skipped (no credentials)")
        return

    # Simple video post (not the multi-phase /video_reels endpoint) — publishes
    # as a Page video. It may or may not surface in the dedicated Reels tab
    # depending on aspect ratio/duration; see README for the caveat.
    resp = requests.post(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/videos",
        data={"file_url": video_url, "description": caption, "access_token": token},
        timeout=60,
    )
    if resp.status_code == 200:
        print("[fb-video] تم نشر الفيديو بنجاح.")
    else:
        print(f"[fb-video] فشل النشر: {resp.status_code} {resp.text[:300]}")


def publish_tiktok_video(video_url, caption):
    token = os.environ.get("TIKTOK_ACCESS_TOKEN")
    if not token:
        print("[tiktok-video] skipped (no credentials)")
        return

    # NOTE: "privacy_level" PUBLIC_TO_EVERYONE requires your TikTok app to
    # have passed Content Posting API audit. Unaudited/sandbox apps can only
    # post as SELF_ONLY (visible in the account's own TikTok app, not public).
    privacy_level = os.environ.get("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY")

    resp = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "post_info": {
                "title": caption[:150],
                "privacy_level": privacy_level,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        },
        timeout=30,
    )
    if resp.status_code == 200:
        print(f"[tiktok-video] تم إرسال الفيديو للنشر (privacy_level={privacy_level}).")
    else:
        print(f"[tiktok-video] فشل النشر: {resp.status_code} {resp.text[:300]}")


# --------------------------------------------------------------------------
# Entry point called from auto_publish.py
# --------------------------------------------------------------------------
def create_and_publish_promo_video(item, blog_url):
    caption = (
        item.get("title", "")
        + ("\n\n" + blog_url if blog_url else "")
    ).strip()

    with tempfile.TemporaryDirectory() as tmp_dir:
        video_path = pathlib.Path(tmp_dir) / "promo.mp4"
        print("[promo-video] جارٍ إنشاء الفيديو...")
        build_video(item["image_url"], item.get("title", ""), video_path)

        print("[promo-video] جارٍ رفع الفيديو للحصول على رابط عام...")
        video_url = upload_as_github_release_asset(video_path)

    print("[promo-video] جارٍ النشر على المنصات الاجتماعية...")
    publish_instagram_reel(video_url, caption)
    publish_facebook_video(video_url, caption)
    publish_tiktok_video(video_url, caption)
