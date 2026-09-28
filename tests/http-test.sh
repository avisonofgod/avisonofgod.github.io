#!/bin/bash
# Pruebas del sitio servido por HTTP (como quedará en GitHub Pages).
# Uso: bash tests/http-test.sh [puerto]
set -uo pipefail
cd "$(dirname "$0")/.."
PORT="${1:-8099}"
OK=0; FAIL=0
chk() { if [ "$2" = "1" ]; then echo "OK   $1${3:+ | $3}"; OK=$((OK+1)); else echo "FALLA $1${3:+ | $3}"; FAIL=$((FAIL+1)); fi; }

python3 -m http.server "$PORT" >/tmp/tanaj-http.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.25; done

code() { curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT$1"; }
ctype() { curl -s -o /dev/null -w "%{content_type}" "http://127.0.0.1:$PORT$1"; }
bytes() { curl -s -o /dev/null -w "%{size_download}" "http://127.0.0.1:$PORT$1"; }

chk "portada 200" "$([ "$(code /)" = 200 ] && echo 1 || echo 0)"
chk "index.json 200" "$([ "$(code /v1/index.json)" = 200 ] && echo 1 || echo 0)"
chk "he/bereshit/1.json 200" "$([ "$(code /v1/he/bereshit/1.json)" = 200 ] && echo 1 || echo 0)"
chk "es/devarim/6.json 200" "$([ "$(code /v1/es/devarim/6.json)" = 200 ] && echo 1 || echo 0)"
chk "search/ketuvim.json 200" "$([ "$(code /v1/search/ketuvim.json)" = 200 ] && echo 1 || echo 0)"
chk "align.json 200" "$([ "$(code /v1/align.json)" = 200 ] && echo 1 || echo 0)"
chk "manifest.json 200" "$([ "$(code /v1/manifest.json)" = 200 ] && echo 1 || echo 0)"
chk "api.html 200" "$([ "$(code /api.html)" = 200 ] && echo 1 || echo 0)"
chk "sw.js 200" "$([ "$(code /sw.js)" = 200 ] && echo 1 || echo 0)"
chk "404 real" "$([ "$(code /v1/he/bereshit/99.json)" = 404 ] && echo 1 || echo 0)"

CT=$(ctype /v1/he/bereshit/1.json)
chk "content-type JSON" "$([ "$(curl -s -o /dev/null -w '%{content_type}' "http://127.0.0.1:$PORT/v1/he/bereshit/1.json" | grep -c json)" = 1 ] && echo 1 || echo 0)" "$CT"

B=$(bytes /index.html)
chk "portada ligera (< 60 KB)" "$([ "$B" -lt 60000 ] && echo 1 || echo 0)" "$B B"

# contenido servido correcto (hebreo y español del Shemá)
PORT_N="$PORT" python3 - <<'PY' > /tmp/tanaj-http-check.txt
import json, os, urllib.request
base = "http://127.0.0.1:" + os.environ["PORT_N"]
d = json.load(urllib.request.urlopen(base + "/v1/he/devarim/6.json"))
e = json.load(urllib.request.urlopen(base + "/v1/es/devarim/6.json"))
print("he:", d["verses"][3]["he_plain"][:20])
print("es:", e["verses"][3]["es"][:20])
print("counts:", d["counts"]["verses"], e["counts"]["verses"])
PY
chk "Devarim 6:4 hebreo servido" "$(grep -c '^he: שמע' /tmp/tanaj-http-check.txt)"
chk "Devarim 6:4 español servido" "$(grep -c '^es: Oye, Israel' /tmp/tanaj-http-check.txt)"
chk "25 versículos en Devarim 6" "$(grep -c '^counts: 25 25' /tmp/tanaj-http-check.txt)"

echo
echo "== RESUMEN: $OK OK / $FAIL FALLA =="
[ "$FAIL" = 0 ] || exit 1
