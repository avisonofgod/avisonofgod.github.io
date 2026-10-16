#!/bin/bash
# Baja (o actualiza) las fuentes del Tanaj a data/ — data/ NO se versiona.
#
#   hebreo : Westminster Leningrad Codex con morfología (morphhb, CC BY 4.0)
#   español: Reina-Valera 1909, dominio público (API getbible v2, sin clave)
#   puente : Reina-Valera 1865 con números de Strong a nivel de palabra (CC0-1.0),
#            solo para GENERAR la capa propia build/es_strong/ (no se sirve tal cual)
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

RV1865_PIN=b399c0a135a8698392d841be6c421f6a68c27c6a
RV1865_URL=https://raw.githubusercontent.com/ohneklavier-creator/reina-valera-1865-strongs-concordancia/$RV1865_PIN/json/rv1865
RV1865_FILES="01-genesis 02-exodus 03-leviticus 04-numbers 05-deuteronomy 06-joshua
  07-judges 08-ruth 09-1-samuel 10-2-samuel 11-1-kings 12-2-kings 13-1-chronicles
  14-2-chronicles 15-ezra 16-nehemiah 17-esther 18-job 19-psalms 20-proverbs
  21-ecclesiastes 22-song-of-solomon 23-isaiah 24-jeremiah 25-lamentations 26-ezekiel
  27-daniel 28-hosea 29-joel 30-amos 31-obadiah 32-jonah 33-micah 34-nahum
  35-habakkuk 36-zephaniah 37-haggai 38-zechariah 39-malachi"

if [ "$FORCE" = "--force" ] || [ ! -d data/rv1865_strongs ]; then
  echo "== puente Strong: bajando RV1865 etiquetada (CC0) =="
  mkdir -p data/rv1865_strongs
  for f in $RV1865_FILES; do
    curl -sSfL -o "data/rv1865_strongs/$f.json" "$RV1865_URL/$f.json"
  done
else
  echo "== puente Strong: data/rv1865_strongs ya existe (usa --force para actualizar) =="
fi

echo
echo "== fuentes =="
echo -n "wlc XML: "; ls data/morphhb/wlc/*.xml 2>/dev/null | wc -l
sha256sum data/morphhb/wlc/Gen.xml 2>/dev/null | cut -c1-16 | sed 's/^/sha256(Gen.xml) /'
if [ -s data/valera.json ]; then
  echo -n "valera.json bytes: "; wc -c < data/valera.json
  sha256sum data/valera.json | cut -c1-16 | sed 's/^/sha256(valera)  /'
fi
echo -n "rv1865 etiquetada: "; ls data/rv1865_strongs/*.json 2>/dev/null | wc -l
