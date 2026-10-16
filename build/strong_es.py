"""Retro-etiquetado del español del Tanaj con números de Strong (capa propia v1.0 עבדיהו).

Qué hace
--------
El español de la API (RV1909 + las capas de `build/es_versions/`) NO trae números de
Strong: `data/valera.json` lo anuncia pero 0 de 31.084 versículos lo traen. Este módulo
construye la relación palabra hebrea <-> palabra española con un puente Strong:

  WLC (morphhb)                  RV1865 etiquetada (CC0)        texto propio
  palabra hebrea -> H####   <->  palabra española -> H####  ==>  token ES -> H####

Para cada versículo se mapean las etiquetas de la RV1865 al texto español que sirve la
API (que puede estar reescrito por la capa de Obadias) usando la posición declarada
(`pos`, 0-based) más un desplazamiento constante por versículo (moda de los aciertos
exactos) y, si no cuadra, emparejamiento monótono por palabra normalizada.

Salida (versionada, es la fuente de verdad del etiquetado)
    build/es_strong/obadias-v1.0-strong.json
      books.<slug>.<capítulo>.<versículo> = [Strong|null, ...]  (paralelo a los tokens
      del texto español que sirve `v1/es/...`, separados por espacios)

Uso
    python3 build/strong_es.py                       # los 39 libros
    python3 build/strong_es.py --books bereshit      # uno (pruebas)
    python3 build/strong_es.py --dry                 # no escribe, solo informe
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_data                                # noqa: E402
import curated                                   # noqa: E402
import es_verses                                 # noqa: E402
import slugs                                     # noqa: E402
import wlc                                       # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "build", "es_strong", "obadias-v1.0-strong.json")
RV1865_DIR = os.path.join(RAIZ, "data", "rv1865_strongs")

META = {
    "version": "1.0",
    "short": "v1.0",
    "author": "Obadias (עבדיהו)",
    "license": "CC0 1.0 Universal (dedicación al dominio público)",
    "spdx": "CC0-1.0",
    "source": ("Retro-etiquetado propio del texto español de la API: WLC con morfología "
               "(openscriptures/morphhb, CC BY 4.0) + Reina-Valera 1865 con números de "
               "Strong a nivel de palabra (ohneklavier-creator/reina-valera-1865-strongs-"
               "concordancia, CC0-1.0)"),
    "note": ("Los Strong marcan el TOKEN español (separado por espacios) que corresponde a "
             "la palabra hebrea del mismo versículo. `null` = palabra española sin etiqueta "
             "(artículos, preposiciones, conjunciones)."),
}

STRONG_RE = re.compile(r"[HG]\d+")
ACCENT = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def norm(txt):
    """Minúsculas, sin acentos, sin puntuación: para cotejar etiquetas con tokens."""
    t = unicodedata.normalize("NFD", (txt or "").lower()).translate(ACCENT)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "".join(c for c in t if c.isalnum())


def he_words(body):
    """[(palabra_hebrea, strong_o_None)] del versículo, en el orden del texto servido."""
    body = wlc.NOTE_RE.sub(" ", body)
    words, cur, curstrong = [], [], []

    def flush():
        if cur:
            w = "".join(cur).strip()
            if w:
                words.append((w, curstrong[0] if curstrong else None))
            cur.clear()
            curstrong.clear()

    for m in TOK_RE.finditer(body):
        if m.group(1) is not None:
            flush()
            cur.append(wlc._text(m.group(2)).replace("/", ""))
            lm = LEMMA_RE.search(m.group(1))
            nums = re.findall(r"\d+", lm.group(1)) if lm else []
            curstrong.append("H" + nums[-1] if nums else None)
        else:
            typ, txt = m.group(3), wlc._text(m.group(4)).strip()
            if typ == "x-maqqef":
                cur.append(wlc.MAQQEF)
            elif typ == "x-sof-pasuq":
                cur.append(wlc.SOF_PASUQ)
            elif typ == "x-paseq":
                flush()
                words.append((wlc.PASEQ, None))
            elif typ in wlc.PARA_MARKS:
                pass
            elif txt:
                cur.append(txt)
    flush()
    return words


def es_textos(capas, valera, wlc_dir):
    """{(slug, cap, n): (texto_es, cita_es)} del texto que sirve la API (capa incluida).

    En los libros con regla curada (Yoel, Malaquías) el versículo lleva numeración hebrea
    y `cita_es` da la referencia de la RV1909 («3:1»), que es la que usa la fuente etiquetada.
    """
    es_src = build_data.load_valera(valera)
    out = {}
    for book in slugs.BOOKS:
        chaps = es_src.get(book["rv1909"], {})
        es_verses.apply(chaps, book["slug"], capas)
        xml = os.path.join(wlc_dir, book["osis"] + ".xml")
        he_caps = sorted(wlc.parse_book(xml)) if os.path.isfile(xml) else []
        for num in he_caps:                     # se recorre el capítulo HEBREO (como el build)
            cur = curated.slice_es(chaps, book["slug"], num)
            if cur is not None:
                for n, txt, ref in cur:
                    out[(book["slug"], num, n)] = (txt, ref)
                continue
            for r in chaps.get(num, []):
                out[(book["slug"], num, r["n"])] = (r["es"], None)
    return out


def etiquetas_rv1865():
    """{'bereshit': {cap: {n: [(pos, palabra, Strong), ...]}}} desde data/rv1865_strongs/."""
    por_en = {b["en"].lower(): b["slug"] for b in slugs.BOOKS}
    alias = {"psalm": "psalms", "song of solomon": "song of songs",
             "songs of solomon": "song of songs", "canticles": "song of songs"}
    salida, sin_libro = {}, []
    for nombre in sorted(os.listdir(RV1865_DIR)):
        if not nombre.endswith(".json"):
            continue
        raw = json.load(open(os.path.join(RV1865_DIR, nombre), encoding="utf-8"))
        if raw.get("testament") != "OT":
            continue
        clave = (raw.get("book") or "").strip().lower()
        slug = por_en.get(clave) or por_en.get(alias.get(clave, ""))
        if not slug:
            sin_libro.append((nombre, raw.get("book")))
            continue
        cap_out = {}
        for cap, versos in raw.get("chapters", {}).items():
            v_out = {}
            for n, items in versos.items():
                filas = []
                for it in items or []:
                    st = STRONG_RE.findall(str(it.get("strongs") or ""))
                    if st:
                        filas.append((int(it.get("pos") or 0), it.get("word") or "", st[0]))
                v_out[int(n)] = sorted(filas)
            cap_out[int(cap)] = v_out
        salida[slug] = cap_out
    if sin_libro:
        print("AVISO: sin slug para %s" % sin_libro)
    return salida


def etiquetar(tokens, filas):
    """[Strong|None] por token español. Devuelve (etiquetas, exactos, asignados, offset)."""
    etiquetas = [None] * len(tokens)
    normas = [norm(t) for t in tokens]
    # 1) aciertos exactos monótonos -> desplazamiento más común
    deltas, ultimo, exactos = Counter(), -1, 0
    for pos, palabra, _st in filas:
        pn = norm(palabra)
        if not pn:
            continue
        for i in range(ultimo + 1, len(tokens)):
            if normas[i] == pn:
                deltas[i - pos] += 1
                ultimo = i
                exactos += 1
                break
    offset = deltas.most_common(1)[0][0] if deltas else 0
    # 2) asignación por posición (+offset), con un hueco de tolerancia
    asignados = 0
    for pos, palabra, st in filas:
        objetivo = pos + offset
        if 0 <= objetivo < len(tokens) and etiquetas[objetivo] is None:
            etiquetas[objetivo] = st
            asignados += 1
            continue
        # hueco: el token vecino libre más cercano (el texto pudo reescribirse)
        for d in (1, -1, 2, -2, 3, -3):
            j = objetivo + d
            if 0 <= j < len(tokens) and etiquetas[j] is None:
                etiquetas[j] = st
                asignados += 1
                break
    return etiquetas, exactos, asignados, offset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wlc", default=os.path.join(RAIZ, "data", "morphhb", "wlc"))
    ap.add_argument("--valera", default=os.path.join(RAIZ, "data", "valera.json"))
    ap.add_argument("--out", default=SALIDA)
    ap.add_argument("--books", default=None, help="slug o lista separada por comas")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(RV1865_DIR):
        sys.exit("falta %s (bash build/fetch_sources.sh)" % RV1865_DIR)
    capas = es_verses.load()
    textos = es_textos(capas, args.valera, args.wlc)
    tags = etiquetas_rv1865()

    quiere = set(args.books.split(",")) if args.books else None
    libros = [b for b in slugs.BOOKS if (not quiere or b["slug"] in quiere)]
    out_books, stats = {}, Counter()
    for book in libros:
        xml = os.path.join(args.wlc, book["osis"] + ".xml")
        if not os.path.isfile(xml):
            sys.exit("falta la fuente hebrea: %s" % xml)
        versos = tags.get(book["slug"], {})
        propios = sorted(k for k in textos if k[0] == book["slug"])
        por_cap = {}
        for _slug, cap, n in propios:
            txt, cita = textos[(_slug, cap, n)]
            por_vers = versos.get(cap, {})
            filas = por_vers.get(n)
            if filas is None and cita:          # libro curado: la cita usa otra numeración
                try:
                    c2, n2 = (int(x) for x in str(cita).split(":"))
                    filas = versos.get(c2, {}).get(n2)
                except (TypeError, ValueError):
                    filas = None
            filas = filas or []
            tokens = txt.split()
            et, exactos, asignados, _off = etiquetar(tokens, filas)
            stats["versiculos"] += 1
            stats["tokens"] += len(tokens)
            stats["tokens_etiquetados"] += sum(1 for e in et if e)
            stats["etiquetas"] += len(filas)
            stats["aciertos_exactos"] += exactos
            stats["asignados_por_posicion"] += asignados
            if not filas:
                stats["versiculos_sin_fuente"] += 1
            elif not asignados:
                stats["versiculos_sin_etiqueta"] += 1
            por_cap.setdefault(cap, {})[n] = et
        out_books[book["slug"]] = por_cap

    payload = dict(META, stats=dict(stats), books=out_books)
    if args.dry:
        print("(dry) libros=%d" % len(out_books))
    else:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with open(args.out, "wb") as fh:
            fh.write(blob)
        print("escrito %s (%.2f MB)" % (args.out, len(blob) / 1048576))

    print("versículos %d | tokens %d | tokens con Strong %d (%.1f%%)"
          % (stats["versiculos"], stats["tokens"], stats["tokens_etiquetados"],
             100 * stats["tokens_etiquetados"] / max(1, stats["tokens"])))
    print("etiquetas %d | exactas %d (%.1f%%) | por posición %d | versículos sin etiqueta %d"
          % (stats["etiquetas"], stats["aciertos_exactos"],
             100 * stats["aciertos_exactos"] / max(1, stats["etiquetas"]),
             stats["asignados_por_posicion"], stats["versiculos_sin_etiqueta"]))
    if stats["versiculos_sin_fuente"]:
        print("versículos sin fuente etiquetada (RV1865 no los cubre): %d"
              % stats["versiculos_sin_fuente"])


if __name__ == "__main__":
    main()
