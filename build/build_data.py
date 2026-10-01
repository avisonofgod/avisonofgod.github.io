"""Genera la API estática del Tanaj en `v1/` (opción A: GitHub Pages es la API).

Uso:
    python3 build/build_data.py --wlc data/morphhb/wlc --valera data/valera.json --out v1
    python3 build/build_data.py --lang he          # solo hebreo
    python3 build/build_data.py --book bereshit    # un libro (pruebas)
    python3 build/build_data.py --books            # además v1/books/<slug>.json (libro entero)

Salida:
    v1/index.json                       metadatos (secciones, libros, alias, conteos)
    v1/manifest.json                    ruta -> {bytes, sha256}
    v1/he/<slug>/<cap>.json             hebreo (WLC: niqqud + te'amim)
    v1/es/<slug>/<cap>.json             español (Reina-Valera 1909)
    v1/search/<seccion>.json            índice de búsqueda (texto normalizado)

Sin dependencias externas: solo la biblioteca estándar.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import curated                                  # noqa: E402
import es_verses                                # noqa: E402
import slugs                                    # noqa: E402
import wlc                                      # noqa: E402

ACCENT_MAP = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def norm_es(text):
    """Español normalizado para búsqueda (minúsculas, sin acentos, sin puntuación)."""
    t = unicodedata.normalize("NFC", text or "").lower().translate(ACCENT_MAP)
    t = re.sub(r"[^0-9a-zא-ת ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def write_json(path, payload, manifest):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    blob = data.encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(blob)
    manifest[path] = {"bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
    return len(blob)


def load_valera(path):
    """{nombre_es: {capítulo: [versículos]}} desde el JSON de getbible v2."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    books = raw["books"] if isinstance(raw, dict) else raw
    out = {}
    for b in books:
        name = (b.get("name") or "").strip()
        if name not in slugs.BY_RV:
            continue
        chaps = {}
        for ch in b.get("chapters", []):
            num = int(ch.get("chapter") or ch.get("nr") or 0)
            chaps[num] = [{"n": int(v.get("verse") or i + 1), "es": (v.get("text") or "").strip()}
                          for i, v in enumerate(ch.get("verses", []))]
        out[name] = chaps
    return out


def chapter_ref(book, num):
    return "%s %d" % (book["he"], num)


def build(args):
    manifest = {}
    es_src = load_valera(args.valera) if args.lang in ("all", "es") else {}
    targets = [b for b in slugs.BOOKS
               if not args.book or b["slug"] == args.book or b["osis"] == args.book]
    if not targets:
        sys.exit("libro no encontrado: %s" % args.book)

    total_bytes = 0
    search = {s: [] for s in slugs.SECTIONS}
    missing_es = []
    alignment_rows = []
    tot_he_v = tot_es_v = tot_he_c = 0

    for book in targets:
        xml = os.path.join(args.wlc, book["osis"] + ".xml")
        if not os.path.isfile(xml):
            sys.exit("falta la fuente hebrea: %s" % xml)
        he_chaps = wlc.parse_book(xml)
        es_chaps = es_src.get(book["rv1909"], {})
        es_verses.apply(es_chaps, book["slug"])

        n_verses_he = sum(len(v) for v in he_chaps.values())
        n_verses_es = sum(len(v) for v in es_chaps.values())
        tot_he_v += n_verses_he
        tot_es_v += n_verses_es
        tot_he_c += len(he_chaps)
        book["chapters"] = len(he_chaps)
        book["verses"] = n_verses_he
        book["verses_es"] = n_verses_es

        for num in sorted(he_chaps):
            verses = he_chaps[num]
            es = {v["n"]: v["es"] for v in es_chaps.get(num, [])}
            es_ov = {v["n"] for v in es_chaps.get(num, []) if v.get("es_override")}
            if (args.lang in ("all", "es") and not es
                    and not curated.slice_es(es_chaps, book["slug"], num)):
                missing_es.append("%s/%d" % (book["slug"], num))

            if args.lang in ("all", "he"):
                payload = {
                    "ref": chapter_ref(book, num),
                    "ref_en": "%s %d" % (book["en"], num),
                    "book": {"slug": book["slug"], "he": book["he"], "es": book["es"],
                             "en": book["en"], "section": book["section"], "order": book["order"]},
                    "chapter": num,
                    "lang": "he",
                    "source": "Westminster Leningrad Codex (morphhb, CC BY 4.0)",
                    "verses": [{"n": v["n"], "he": v["he"], "he_plain": v["he_plain"],
                                **({"marker": v["marker"]} if v.get("marker") else {})}
                               for v in verses],
                    "counts": {"verses": len(verses)},
                }
                total_bytes += write_json(
                    os.path.join(args.out, "he", book["slug"], "%d.json" % num), payload, manifest)

            cur = curated.slice_es(es_chaps, book["slug"], num)
            if cur is not None:
                if len(cur) != len(verses):
                    sys.exit("regla curada de %s/%d no cuadra: %d he vs %d es"
                             % (book["slug"], num, len(verses), len(cur)))
                es_rows = [{"n": n, "es": txt, "es_ref": ref} for n, txt, ref in cur]
            else:
                es_rows = [{"n": n, "es": es[n], **({"es_override": True} if n in es_ov else {})}
                           for n in sorted(es)]

            if args.lang in ("all", "es") and (es_rows or []):
                payload = {
                    "ref": "%s %d" % (book["es"], num),
                    "ref_en": "%s %d" % (book["en"], num),
                    "book": {"slug": book["slug"], "he": book["he"], "es": book["es"],
                             "en": book["en"], "section": book["section"], "order": book["order"]},
                    "chapter": num,
                    "lang": "es",
                    "source": "Reina-Valera 1909 (dominio público)",
                    "verses": es_rows,
                    "counts": {"verses": len(es_rows)},
                    "alignment": {"he": len(verses), "es": len(es_rows),
                                  "diff": len(es_rows) - len(verses),
                                  "same_numbering": len(es_rows) == len(verses),
                                  "curated": cur is not None},
                }
                if cur is not None:
                    payload["note"] = ("numeración propia de la RV1909 reubicada en el capítulo "
                                       "hebreo; usa es_ref para la cita original")
                    alignment_rows.append({
                        "slug": book["slug"], "chapter": num, "type": "capitulos_distintos",
                        "he_verses": len(verses), "es_verses": len(es_rows)})
                elif len(es_rows) != len(verses):
                    alignment_rows.append({
                        "slug": book["slug"], "chapter": num, "type": "versiculo_desplazado",
                        "he_verses": len(verses), "es_verses": len(es_rows),
                        "diff": len(es_rows) - len(verses)})
                total_bytes += write_json(
                    os.path.join(args.out, "es", book["slug"], "%d.json" % num), payload, manifest)

            # el índice de búsqueda usa el MISMO español que sirve la API (alineado)
            es_por_n = {}
            for i, v in enumerate(verses):
                if cur is not None:
                    es_por_n[v["n"]] = es_rows[i]["es"] if i < len(es_rows) else ""
                else:
                    es_por_n[v["n"]] = es.get(v["n"], "")
            for v in verses:
                search[book["section"]].append(
                    ["%s/%d/%d" % (book["slug"], num, v["n"]), v["he_plain"],
                     norm_es(es_por_n.get(v["n"], ""))])

        if args.books:
            total_bytes += write_json(
                os.path.join(args.out, "books", "%s.json" % book["slug"]),
                {"book": {"slug": book["slug"], "he": book["he"], "es": book["es"],
                          "en": book["en"], "section": book["section"], "order": book["order"]},
                 "chapters": {"he": he_chaps, "es": es_chaps}},
                manifest)

    for section, rows in search.items():
        if not rows:
            continue
        total_bytes += write_json(
            os.path.join(args.out, "search", "%s.json" % section),
            {"section": section, "format": "compact-v1",
             "note": "verses: [referencia, hebreo sin niqqud, español normalizado]",
             "count": len(rows), "verses": rows},
            manifest)

    if not args.book:
        if (not args.no_check) and (tot_he_c != 929 or tot_he_v != 23213):
            sys.exit("AUTOCOMPROBACION FALLIDA: hebreo %d capitulos / %d versiculos "
                     "(esperado 929 / 23213)" % (tot_he_c, tot_he_v))
        write_json(os.path.join(args.out, "align.json"), {
            "note": ("Diferencias de numeración entre el Tanaj (WLC) y la RV1909. "
                     "`capitulos_distintos`: la RV1909 parte el libro en otros capítulos "
                     "(el español se reubica y trae es_ref). `versiculo_desplazado`: el mismo "
                     "capítulo tiene otro número de versículos; cada idioma conserva su número."),
            "curated": sorted(curated.CURATED.keys()),
            "chapters": sorted(alignment_rows, key=lambda r: (r["slug"], r["chapter"])),
        }, manifest)
        _idx = slugs.index_payload()
        _idx["counts"]["verses_es"] = tot_es_v
        _idx["sources"] = {
            "he": "Westminster Leningrad Codex con morfología (openscriptures/morphhb, CC BY 4.0)",
            "es": "Reina-Valera 1909 (dominio público, getbible v2)",
        }
        _idx["alignment"] = {"file": "align.json",
                             "chapters_with_divergence": len(alignment_rows),
                             "curated_books": sorted(curated.CURATED.keys())}
        write_json(os.path.join(args.out, "index.json"), _idx, manifest)
        write_json(os.path.join(args.out, "manifest.json"),
                   {"generated_by": "build/build_data.py", "files": manifest,
                    "counts": dict(slugs.index_payload()["counts"], verses_es=tot_es_v)},
               manifest)
    else:
        print("(--book: sin index.json/manifest.json, build parcial)")

    if missing_es:
        print("AVISO: capítulos sin texto español: %d (%s…)" %
              (len(missing_es), ", ".join(missing_es[:5])))
    print("libros=%d capitulos=%d versiculos_he=%d versiculos_es=%d archivos=%d bytes=%d" %
          (len(targets), tot_he_c, tot_he_v, tot_es_v, len(manifest), total_bytes))


def main():
    ap = argparse.ArgumentParser(description="Genera la API estática del Tanaj")
    ap.add_argument("--wlc", default="data/morphhb/wlc", help="carpeta con los XML del WLC")
    ap.add_argument("--valera", default="data/valera.json", help="JSON de la RV1909")
    ap.add_argument("--out", default="v1", help="carpeta de salida")
    ap.add_argument("--lang", default="all", choices=["all", "he", "es"])
    ap.add_argument("--book", default=None, help="slug u OSIS de un solo libro")
    ap.add_argument("--books", action="store_true", help="generar también v1/books/<slug>.json")
    ap.add_argument("--no-check", action="store_true", help="no exigir 929 capítulos / 23213 versículos")
    build(ap.parse_args())


if __name__ == "__main__":
    main()
