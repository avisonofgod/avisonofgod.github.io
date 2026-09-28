#!/bin/bash
# Baja (o actualiza) las fuentes del Tanaj a data/ — data/ NO se versiona.
#
#   hebreo : Westminster Leningrad Codex con morfología (morphhb, CC BY 4.0)
#   español: Reina-Valera 1909, dominio público (API getbible v2, sin clave)
#
# Uso: bash build/fetch_sources.sh [--force]
set -euo pipefail

cd "$(dirname "$0")/.."
FORCE="${1:-}"
mkdir -p data

if [ "$FORCE" = "--force" ] || [ ! -d data/morphhb/wlc ]; then
  echo "== hebreo: clonando morphhb =="
  rm -rf data/morphhb
  git clone --depth 1 -q https://github.com/openscriptures/morphhb data/morphhb
else
  echo "== hebreo: data/morphhb ya existe (usa --force para actualizar) =="
fi

if [ "$FORCE" = "--force" ] || [ ! -s data/valera.json ]; then
  echo "== español: bajando RV1909 (getbible v2) =="
  curl -sSfL -o data/valera.json https://api.getbible.net/v2/valera.json
else
  echo "== español: data/valera.json ya existe (usa --force para actualizar) =="
fi

echo
echo "== fuentes =="
echo -n "wlc XML: "; ls data/morphhb/wlc/*.xml 2>/dev/null | wc -l
sha256sum data/morphhb/wlc/Gen.xml 2>/dev/null | cut -c1-16 | sed 's/^/sha256(Gen.xml) /'
if [ -s data/valera.json ]; then
  echo -n "valera.json bytes: "; wc -c < data/valera.json
  sha256sum data/valera.json | cut -c1-16 | sed 's/^/sha256(valera)  /'
fi
