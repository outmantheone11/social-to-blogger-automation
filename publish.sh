#!/usr/bin/env bash
# نشر كامل: فحص -> commit -> push -> انتظار jsDelivr -> توليد -> رفع Blogger -> تحقق من الصفحة الحية
set -Eeuo pipefail
cd "$(dirname "$0")"
mkdir -p logs
LOG="logs/publish-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

REPO="outmantheone11/social-to-blogger-automation"
PAGE_ID="${PAGE_ID:-2288061485082308217}"
LIVE_URL="https://wassata-tijaria-akaria.blogspot.com/p/wassata-tijaria-akaria-real-estate.html"
STAGE="بدء"

on_error(){ echo "❌ فشلت المرحلة: $STAGE (السطر $1)"; echo "   السجل: $LOG"; }
trap 'on_error $LINENO' ERR

stage(){ STAGE="$1"; echo; echo "▶ [$(date +%T)] $1"; }
retry(){ local n=$1; shift; local i; for i in $(seq 1 "$n"); do "$@" && return 0; echo "  ↻ محاولة $i/$n فشلت" >&2; sleep $((i*5)); done; return 1; }

[ -f .env ] && { set -a; . ./.env; set +a; }
for v in GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET GOOGLE_REFRESH_TOKEN BLOGGER_BLOG_ID; do
  [ -n "${!v:-}" ] || { echo "❌ المتغير $v غير مضبوط"; exit 1; }
done

stage "1 فحص الصياغة"
node --check app.js
echo "✔ app.js صالح"

stage "2 commit و push"
if git diff --quiet -- app.js; then
  echo "لا تغييرات في app.js"
else
  git add app.js
  git commit -m "${1:-update $(date +%F)}"
  git push origin HEAD:main
fi
HASH=$(git rev-parse HEAD)
git fetch -q origin main
git merge-base --is-ancestor "$HASH" origin/main
echo "✔ commit: $HASH"

stage "3 انتظار jsDelivr"
jsd(){ curl -sf "https://cdn.jsdelivr.net/gh/$REPO@$HASH/app.js" | grep -q "var TESTIMONIALS"; }
retry 12 jsd
echo "✔ الملف متاح على jsDelivr"

stage "4 توليد الصفحة"
APP_HASH="$HASH" python3 fix_page.py

stage "5 رفع إلى Blogger"
get_token(){ curl -sf https://oauth2.googleapis.com/token -d client_id="$GOOGLE_CLIENT_ID" -d client_secret="$GOOGLE_CLIENT_SECRET" -d refresh_token="$GOOGLE_REFRESH_TOKEN" -d grant_type=refresh_token | jq -re .access_token; }
ACCESS=$(retry 3 get_token)
upload(){ jq -n --rawfile c page_fixed.html '{content:$c}' | curl -sf -X PATCH "https://www.googleapis.com/blogger/v3/blogs/$BLOGGER_BLOG_ID/pages/$PAGE_ID" -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" -d @- | jq -e '.updated' >/dev/null; }
retry 3 upload
echo "✔ تم الرفع"

stage "6 تحقق من الصفحة الحية"
live(){ curl -sf "$LIVE_URL" -o /tmp/live.html && grep -q "$HASH" /tmp/live.html && ! grep -q "claude:viewport" /tmp/live.html; }
retry 8 live
echo
echo "✅ نُشرت الصفحة على commit $HASH"
echo "   السجل: $LOG"
