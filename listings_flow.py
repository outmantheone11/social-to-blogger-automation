import os, re, sys, json, pathlib, datetime
import anthropic
from auto_publish import get_blogger_service
from listings_update import insert_listing, ALLOWED_CAT, ALLOWED_MEDIA

BLOG_ID = os.environ["BLOGGER_BLOG_ID"]
PAGE_ID = os.environ.get("BLOGGER_PAGE_ID", "2288061485082308217")
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
PENDING = pathlib.Path("state/pending_listings.json")

PROMPT = """من نص المنشور التالي استخرج بيانات عرض عقاري. أعد JSON فقط، بلا شرح ولا علامات ```،
بهذه الحقول بالضبط:
- category: يجب أن يكون حصراً "land" (للأراضي/الضيعات) أو "residential" (للشقق/المنازل/الفيلات/الهنغارات/المحلات).
- media: يجب أن يكون حصراً "land" (أرض) أو "coast" (عقار/أرض ساحلية قرب البحر) أو "res" (مباني/شقق/منازل/هنغارات).
- badge: شارة قصيرة مثل "للبيع · شقة" أو "للبيع · أرض محفظة".
- title: عنوان واضح وجذاب للعرض.
- location: المدينة والحي أو المنطقة.
- area: المساحة كما وردت في النص.
- price: الثمن كما ورد في النص (أو "ثمن قابل للتفاوض" إن لم يُذكر).
- image_url: رابط الصورة إن وُجد في النص، وإلا null.
- video_url: رابط الفيديو (YouTube أو YouTube Shorts أو رابط فيديو مباشر) إن وُجد في النص، وإلا null.
- wa: رسالة واتساب قصيرة جاهزة للاستفسار عن هذا العرض (مثلاً: "مرحباً، أرغب في تفاصيل ...").

إن لم يكن المنشور عرض عقار للبيع فأعد: null

النص:
--
"""

def extract_listing(text):
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=700,
        messages=[{"role": "user", "content": PROMPT + text}]
    )
    out = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    out = re.sub(r"^```(?:json)?|```$", "", out).strip()
    data = json.loads(out)
    if data is None:
        return None
    if data.get("category") not in ALLOWED_CAT:
        data["category"] = "residential"
    if data.get("media") not in ALLOWED_MEDIA:
        data["media"] = "land" if data["category"] == "land" else "res"
    if not data.get("wa"):
        data["wa"] = f"مرحباً، أرغب في الاستفسار عن: {data.get('title', 'العرض العقاري')}"
    return data

def load():
    return json.loads(PENDING.read_text(encoding="utf-8")) if PENDING.exists() else []

def save(items):
    PENDING.parent.mkdir(exist_ok=True)
    PENDING.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def cmd_add(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    data = extract_listing(text)
    if not data:
        print("المنشور ليس عرض عقاري صالح.")
        return
    items = load(); items.append(data); save(items)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("\nأُضيف إلى الانتظار. راجعه ثم نفّذ: python3 listings_flow.py publish")

def cmd_publish():
    items = load()
    if not items:
        print("لا توجد عناصر في الانتظار."); return
    service = get_blogger_service()
    page = service.pages().get(blogId=BLOG_ID, pageId=PAGE_ID, view="ADMIN").execute()
    html_in = page["content"]
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pathlib.Path(f"page_backup_{stamp}.html").write_text(html_in, encoding="utf-8")
    new_html, added = html_in, 0
    for it in items:
        new_html, ok = insert_listing(new_html, it)
        added += ok
    if not added:
        print("كلها مكررة، لم يتغير شيء."); return
    service.pages().patch(blogId=BLOG_ID, pageId=PAGE_ID, body={"content": new_html}).execute()
    save([])
    print(f"نُشر {added} عنصر مع دعم الصور والفيديو. النسخة الاحتياطية: page_backup_{stamp}.html")

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["add"] and len(a) == 2: cmd_add(a[1])
    elif a == ["list"]: print(json.dumps(load(), ensure_ascii=False, indent=2))
    elif a == ["publish"]: cmd_publish()
    else: print("الاستعمال: add FILE | list | publish")
