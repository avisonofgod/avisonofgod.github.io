# Tanaj — lector web + API JSON del Tanaj

El **Tanaj completo** (Torá · Nevi'im · Ketuvim) publicado como página web y como API JSON de
solo lectura, sin backend: **cada archivo del repositorio es un endpoint**.

- **39 libros · 929 capítulos · 23.213 versículos** en hebreo (WLC, con niqqud y te'amim)
- **23.129 versículos** en español (Reina-Valera 1909, dominio público)
- Lector con enlaces permanentes por versículo (`#/devarim/6/4`), búsqueda en hebreo y español,
  modo hebreo/español/ambos, niqqud conmutable y lectura sin conexión (PWA)

Sitio: <https://avisonofgod.github.io/> · Documentación de la API: [`api.html`](api.html)

## Estructura

```
index.html                 lector (una sola página, sin frameworks ni CDN)
api.html                   documentación de la API + atribuciones
sw.js / manifest.webmanifest / icon.svg      PWA (offline)
v1/                        ← la API (generada; se versiona)
  index.json               secciones, orden judío, libros, alias, conteos
  he/<libro>/<cap>.json    hebreo (WLC): `he` con niqqud/te'amim, `he_plain` sin marcas
  es/<libro>/<cap>.json    español (RV1909) + bloque `alignment`
  search/<sección>.json    índice de búsqueda [ref, hebreo sin niqqud, español normalizado]
  align.json               diferencias de numeración hebrea ↔ española
  manifest.json            ruta → bytes y sha256 (integridad)
build/                     generador (Python 3, solo biblioteca estándar)
  fetch_sources.sh         baja las fuentes a data/ (no se versiona)
  slugs.py                 los 39 libros: slug, nombres, sección, orden, alias
  wlc.py                   lector del WLC (OSIS) → texto con niqqud/te'amim en NFC
  curated.py               reglas para Yoel y Malaquías (capítulos repartidos distinto)
  build_data.py            genera v1/ (y autocomprueba 929 capítulos / 23.213 versículos)
  verify_data.py           verificación de integridad, esquema y cobertura
tests/
  test_build.py            pruebas unitarias del generador (stdlib unittest)
  reader-test.js           pruebas del lector con jsdom (navegación, búsqueda, alineación)
data/                      fuentes crudas (ignoradas por git)
```

## Generar la API

```bash
bash build/fetch_sources.sh          # clona morphhb y baja la RV1909 a data/
python3 build/build_data.py --out v1 # escribe v1/ (≈19 MB, 1.864 archivos, ~4 s)
python3 build/verify_data.py v1      # 16 comprobaciones: conteos, sha256, esquema, cobertura
python3 -m unittest discover -s tests -p 'test_*.py'
NODE_PATH=/ruta/node_modules node tests/reader-test.js   # opcional (jsdom)
```

Opciones útiles: `--lang he|es`, `--book bereshit`, `--books` (libro completo en un archivo),
`--no-check` (no exigir los conteos canónicos).

Servir en local:

```bash
python3 -m http.server 8080        # y abrir http://localhost:8080/
```

## API (resumen)

| Ruta | Contenido |
|---|---|
| `/v1/index.json` | metadatos: secciones, libros con alias, conteos, fuentes |
| `/v1/he/<slug>/<cap>.json` | capítulo hebreo: `verses[].he` (niqqud + te'amim), `he_plain`, `marker` |
| `/v1/es/<slug>/<cap>.json` | capítulo español: `verses[].es`, `alignment`, `es_ref` cuando aplica |
| `/v1/search/<sección>.json` | `[referencia, hebreo normalizado, español normalizado]` |
| `/v1/align.json` | divergencias de numeración (142 capítulos) y libros con regla curada |
| `/v1/manifest.json` | bytes y `sha256` por archivo |

`<slug>` es el nombre hebreo transliterado (`bereshit`, `shemot`, `tehillim`…). El lector acepta
alias (`genesis`, `exodo`, `salmos`, `1 samuel`) y los resuelve a la ruta canónica.
Para CORS explícito o caché inmutable por versión:
`https://cdn.jsdelivr.net/gh/avisonofgod/avisonofgod.github.io@main/v1/he/bereshit/1.json`.

## Fuentes y licencias

- **Hebreo** — Westminster Leningrad Codex con niqqud, te'amim y morfología:
  [openscriptures/morphhb](https://github.com/openscriptures/morphhb) (**CC BY 4.0**).
- **Español** — Reina-Valera 1909 (**dominio público**) vía [getbible v2](https://api.getbible.net/).
- No se publican versiones con licencia no comercial (p. ej. JPS/CC-BY-NC).
- El código de este repositorio se publica bajo la licencia del archivo [`LICENSE`](LICENSE).

## Numeración hebrea vs. española

El texto hebreo conserva la numeración masorética y el español la suya; la API **no mezcla**.
`v1/align.json` documenta los 142 capítulos donde difieren:

- `versiculo_desplazado` (135): mismo capítulo con distinto número de versículos
  (p. ej. בְּמִדְבַּר 16 → hebreo 35 / español 50). Cada idioma mantiene su número.
- `capitulos_distintos` (7): en יוֹאֵל y מַלְאָכִי el libro se parte en otros capítulos; el español
  se reubica en el capítulo hebreo y cada versículo guarda `es_ref` con su cita original
  (así Yoel 3:1 lleva `es_ref: "2:28"`).

## Verificación

- `verify_data.py`: conteos canónicos, `sha256` de los 1.864 archivos, esquema de cada capítulo,
  hebreo sin restos de XML y solo con caracteres hebreos, cobertura de la búsqueda, cuadre de las
  reglas curadas. Hoy: **16 OK / 0 FALLA**.
- `tests/test_build.py`: 13 pruebas del parser (maqef, seg anidado, marcas de párrafo, notas, NFC),
  catálogo, alias y build parcial.
- `tests/reader-test.js`: 26 comprobaciones del lector con jsdom sobre la API real (navegación,
  Shemá en hebreo y español, alineación, búsqueda hebrea y española, toggles, enlaces permanentes,
  ausencia de recursos externos).

## Hoja de ruta

- Opción B: Cloudflare Worker `/api/v1` con `?q=`, `?random=1`, CORS y límites.
- Opción C/D: búsqueda por raíz y morfología (morphhb + SQLite FTS5) si se necesita.
- Transliteración española por versículo y comentarios (Rashi/Targum) desde Sefaria, como enlaces.

---
Generado con `build/build_data.py` a partir de las fuentes citadas. Atribución obligatoria en
cualquier reutilización del texto (CC BY 4.0 del OSHB / dominio público de la RV1909).
