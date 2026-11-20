import re, os
SRC, DST = "template/page_source.html", "page_fixed.html"
HASH = os.environ.get("APP_HASH", "")
if len(HASH) < 7: raise SystemExit("APP_HASH مفقود")
WA = "https://wa.me/212708565088"
TEL = "tel:+212708565088"
FB = "https://www.facebook.com/WassataAkariaTijaria?locale=ar_AR"
h = open(SRC, encoding="utf8").read()

# 0) وسم claude: الغريب
h = re.sub(r'<meta content="cover" name="claude:viewport-fit-sides"\s*>(</meta>)?\s*', '', h)

# 1) عنوان واحد فقط
titles = list(re.finditer(r'<title>.*?</title>\s*', h, re.S))
for m in reversed(titles[1:]):
    h = h[:m.start()] + h[m.end():]

# 2) زر FAB مكرر (إبقاء الأول)
fabs = list(re.finditer(r'<div class="fab-stack">.*?</a>\s*</div>', h, re.S))
if len(fabs) > 1:
    m = fabs[-1]
    h = h[:m.start()] + h[m.end():]

# 3) ld+json: إبقاء نسخة واحدة من وسمنا فقط (RealEstateAgent)
ours = list(re.finditer(r'<script type="application/ld\+json">(?:(?!</script>).)*"RealEstateAgent"(?:(?!</script>).)*</script>\s*', h, re.S))
for m in reversed(ours[1:]):
    h = h[:m.start()] + h[m.end():]

# 4) إزالة رابط "آراء العملاء" من القائمتين
h, _ = re.subn(r'<a href="#testimonials">.*?</a>\s*', '', h, flags=re.S)

# 5) الروابط الفارغة
WA_IDS = {"navWaBtn", "heroWaBtn", "cfSubmit", "lfSubmitWa", "fabWaBtn", "footerWaLink"}
TEL_IDS = {"fabCallBtn", "telLink"}
FB_IDS = {"navFbBtn", "footerFbLink", "lfFbLink"}
def fix_tag(m):
    tag = m.group(0)
    i = re.search(r'\bid="([^"]+)"', tag)
    if not i:
        return tag
    k = i.group(1)
    target = WA if k in WA_IDS else TEL if k in TEL_IDS else FB if k in FB_IDS else None
    if target:
        tag = tag.replace('href="#"', f'href="{target}"')
    return tag
h = re.sub(r'<a\b[^>]*>', fix_tag, h)

# 6) مؤشر إصدار app.js (commit ثابت)
h = re.sub(r'social-to-blogger-automation@[^/]+/app\.js',
           f'social-to-blogger-automation@{HASH}/app.js', h)

# 7) خطوات الحاسبة
h = h.replace('id="rPrice" max="10000000"', 'id="rPrice" min="0" max="10000000" step="10000"')
h = h.replace('id="rDown" max="5000000"', 'id="rDown" min="0" max="5000000" step="10000"')
h = h.replace('id="rRate" max="12"', 'id="rRate" min="0" max="12" step="0.1"')
h = h.replace('id="rYears" max="30"', 'id="rYears" min="1" max="30" step="1"')

# 8) النصوص (الأطول أولاً)
R = [
    ("Remove the water from the water. Remove the water from the water.",
     "تقدير تقريبي غير ملزم، ولا يُعد عرضاً تمويلياً من أي بنك."),
    ("Remove the water from the water في", "فرص استثمارية في"),
    ("Remove the water from the water.", "نرد على استفساراتك بسرعة عبر واتساب."),
    ("The full name", "الاسم الكامل"),
    ("The strange questions", "الأسئلة الشائعة"),
    ("Current offers", "العروض الحالية"),
    (">or<", ">أو<"),
    (">details<", ">عقار معروض<"),
    ("سواء اراضي", "سواء أراضٍ"),
]
for a, b in R:
    h = h.replace(a, b)

# 8b) حقن التصميم v2 داخل أول <style>
THEME = open("template/theme.css", encoding="utf8").read()
i = h.find("</style>")
if i < 0:
    raise SystemExit("لا يوجد <style> في الصفحة")
h = h[:i] + "\n/* THEME v2 */\n" + THEME + "\n" + h[i:]

# 9) التحقق قبل الكتابة
checks = {
    "claude_meta": h.count("claude:"),
    "real_estate_ld": h.count('"RealEstateAgent"'),
    "fab": h.count('class="fab-stack"'),
    "testimonial_links": h.count('href="#testimonials"'),
    "water_text": h.count("Remove the water"),
    "app_js_refs": len(re.findall(r'social-to-blogger-automation@' + re.escape(HASH) + r'/app\.js', h)),
}
print(checks)
ok = (checks["claude_meta"] == 0 and checks["real_estate_ld"] == 1 and checks["fab"] == 1
      and checks["testimonial_links"] == 0 and checks["water_text"] == 0 and checks["app_js_refs"] == 1)
if not ok:
    raise SystemExit("فشل التحقق، لم يُكتب الملف")
open(DST, "w", encoding="utf8").write(h)
print("OK:", DST, len(h), "chars")
