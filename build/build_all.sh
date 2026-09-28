#!/bin/bash
# Cadena completa: fuentes -> API -> verificación -> pruebas.
#
#   bash build/build_all.sh            # usa data/ ya descargado
#   bash build/build_all.sh --force    # vuelve a bajar las fuentes
#
# Sale con error si algo no cuadra (conteos, sha256, esquema o pruebas).
set -euo pipefail
cd "$(dirname "$0")/.."

ARGS="${1:-}"
echo "== 1/4 fuentes =="
bash build/fetch_sources.sh $ARGS

echo
echo "== 2/4 generar v1/ =="
python3 build/build_data.py --out v1

echo
echo "== 3/4 verificar =="
python3 build/verify_data.py v1

echo
echo "== 4/4 pruebas =="
python3 -m unittest discover -s tests -p 'test_*.py' 2>&1 | tail -4
if command -v node >/dev/null 2>&1 && [ -d "${NODE_PATH:-/tmp/jtest/node_modules}" ]; then
  NODE_PATH="${NODE_PATH:-/tmp/jtest/node_modules}" node tests/reader-test.js | tail -3
else
  echo "(lector: se omite la prueba con jsdom; define NODE_PATH con jsdom instalado)"
fi

echo
echo "== 5/5 sitio por HTTP =="
bash tests/http-test.sh 8097 | tail -3

echo
echo "== listo =="
du -sh v1 | sed 's/^/tamaño de v1: /'
