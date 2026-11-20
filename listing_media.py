import sys, json
P = "app.js"
s = open(P, encoding="utf8").read()

MEDIA = {
    # "تفاصيل أرض بوسكورة +10000 م²": {
    #     "images": ["media/11cc7041aa427927.jpg", "media/2c7d891c0f7c8bea.jpg"],
    #     "social_url": "https://www.facebook.com/reel/...",
    #     "desc": "وصف تفصيلي للأرض: الموقع، الواجهة، وإمكانيات البناء.",
    # },
}

n = 0
for wa, data in MEDIA.items():
    anchor = f'wa:"{wa}"'
    if s.count(anchor) != 1:
        sys.exit("ERROR: لم يُعثر على العرض بشكل فريد: " + wa)
    idx = s.index(anchor)
    if "images:" in s[max(0, idx - 300):idx] or "desc:" in s[max(0, idx - 300):idx]:
        print("تخطي (موجود مسبقاً):", wa)
        continue
    parts = []
    if data.get("images"):
        parts.append("images:" + json.dumps(data["images"], ensure_ascii=False) + ",")
    if data.get("video_url"):
        parts.append("video_url:" + json.dumps(data["video_url"]) + ",")
    if data.get("social_url"):
        parts.append("social_url:" + json.dumps(data["social_url"]) + ",")
    if data.get("desc"):
        parts.append("desc:" + json.dumps(data["desc"], ensure_ascii=False) + ",")
    s = s[:idx] + "".join(parts) + s[idx:]
    n += 1

open(P, "w", encoding="utf8").write(s)
print("OK: عروض مُحدَّثة =", n)
