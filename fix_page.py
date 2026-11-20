import re
SRC, DST = "page_restored.html", "page_fixed.html"
WA = "https://wa.me/212708565088"
TEL = "tel:+212708565088"
FB = "https://www.facebook.com/"  # ضع رابط صفحتك الحقيقي هنا
h = open(SRC, encoding="utf8").read()

# 1) حذف وسم claude: الغريب
h = re.sub(r'<meta content="cover" name="claude:viewport-fit-sides"></meta>\s*', '', h)
h = re.sub(r'<meta content="cover" name="claude:viewport-fit-sides">\s*', '', h)

# 2) إبقاء عنوان واحد فقط
titles = list(re.finditer(r'<title>.*?</title>\s*', h, re.S))
for m in reversed(titles[1:]):
    h = h[:m.start()] + h[m.end():]

# 3) حذف زر FAB المكرر (إبقاء الأول)
fabs = list(re.finditer(r'<div class="fab-stack">.*?</a>\s*</div>', h, re.S))
if len(fabs) > 1:
    m = fabs[-1]
    h = h[:m.start()] + h[m.end():]

# 4) استبدال href="#" بالروابط الحقيقية
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

# 5) خطوات الحاسبة
h = h.replace('id="rPrice" max="10000000"', 'id="rPrice" min="0" max="10000000" step="10000"')
h = h.replace('id="rDown" max="5000000"', 'id="rDown" min="0" max="5000000" step="10000"')
h = h.replace('id="rRate" max="12"', 'id="rRate" min="0" max="12" step="0.1"')
h = h.replace('id="rYears" max="30"', 'id="rYears" min="1" max="30" step="1"')

# 6) النصوص الخاطئة (الأطول أولاً)
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

open(DST, "w", encoding="utf8").write(h)
print("حجم:", len(h), "| FAB:", h.count('class="fab-stack"'),
      "| claude-meta:", h.count("claude:"), "| Remove-the-water:", h.count("Remove the water"))
