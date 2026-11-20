import sys
P = "app.js"
s = open(P, encoding="utf8").read()
if "صفحة تفاصيل العرض" in s:
    sys.exit("تم الإدراج مسبقاً، لا تغيير")
ANCHOR = 'if(document.readyState==="loading")'
if s.count(ANCHOR) != 1:
    sys.exit("ERROR: نقطة الإدراج غير واضحة")
block = open("template/detail.js", encoding="utf8").read()
s = s.replace(ANCHOR, block + "\n" + ANCHOR)
open(P, "w", encoding="utf8").write(s)
print("OK: أُدرجت صفحة التفاصيل")
