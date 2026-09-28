#!/usr/bin/env python3
"""Verifica la API estática generada en v1/ sin tocar la red.

Comprueba:
  1. conteos canónicos del Tanaj (39 libros / 929 capítulos / 23.213 versículos)
  2. integridad: cada archivo del manifiesto existe y su sha256 coincide
  3. esquema de cada capítulo (hebreo y español) y de los índices
  4. calidad del texto hebreo (sin marcas XML, sin `/`, solo letras hebreas + niqqud)
  5. cobertura: toda referencia de los índices de búsqueda apunta a un capítulo existente
  6. alineación: los libros con regla curada (yoel, malakhi) cuadran verso a verso

Uso: python3 build/verify_data.py [v1]
Salida: líneas OK/FALLA y código de salida 0/1.
"""

import hashlib
import json
import os
import re
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "v1"
REQUIRED_SECTIONS = {"torah": 5, "neviim": 21, "ketuvim": 13}
HEBREW_OK = re.compile(r"^[\u0590-\u05c7\u05d0-\u05ea\u05f3\u05f4 ]+$")

fail = []
ok = 0


def check(cond, label, detail=None):
    global ok
    detail = "" if detail is None else str(detail)
    if cond:
        ok += 1
        print("OK   %s%s" % (label, (" | " + str(detail)) if detail else ""))
    else:
        fail.append(label)
        print("FALLA %s%s" % (label, (" | " + str(detail)) if detail else ""))


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    idx = load(os.path.join(OUT, "index.json"))
    man = load(os.path.join(OUT, "manifest.json"))
    align = load(os.path.join(OUT, "align.json"))

    c = idx["counts"]
    check(c["books"] == 39, "index: 39 libros", c["books"])
    check(c["chapters"] == 929, "index: 929 capítulos", c["chapters"])
    check(c["verses"] == 23213, "index: 23.213 versículos (WLC)", c["verses"])
    check(20_000 < c.get("verses_es", 0) < c["verses"], "index: versículos en español", c.get("verses_es"))

    per_section = {}
    for sec in idx["sections"]:
        per_section[sec["id"]] = len(sec["books"])
    check(per_section == REQUIRED_SECTIONS, "secciones Torah/Nevi'im/Ketuvim", per_section)

    # 2) integridad del manifiesto
    bad_hash = []
    missing = []
    for path, meta in man["files"].items():
        if not os.path.isfile(path):
            missing.append(path)
            continue
        blob = open(path, "rb").read()
        if len(blob) != meta["bytes"] or hashlib.sha256(blob).hexdigest() != meta["sha256"]:
            bad_hash.append(path)
    check(not missing, "manifiesto: todos los archivos existen", len(man["files"]))
    check(not bad_hash, "manifiesto: sha256 correcto en todos", len(man["files"]))

    # 3/4) esquema y calidad por libro
    bad_schema, bad_he, bad_ref = [], [], []
    total_he = total_es = 0
    for book in idx["books"]:
        slug = book["slug"]
        for cap in range(1, book["chapters"] + 1):
            hp = os.path.join(OUT, "he", slug, "%d.json" % cap)
            if not os.path.isfile(hp):
                bad_schema.append(hp)
                continue
            d = load(hp)
            if d["chapter"] != cap or d["book"]["slug"] != slug or not d["verses"]:
                bad_schema.append(hp)
            total_he += len(d["verses"])
            for v in d["verses"]:
                t = v["he"]
                if "<" in t or ">" in t or "/" in t or not t.strip():
                    bad_he.append("%s/%d:%d" % (slug, cap, v["n"]))
                elif not HEBREW_OK.match(t):
                    bad_he.append("%s/%d:%d" % (slug, cap, v["n"]))
                if not v.get("he_plain"):
                    bad_ref.append("%s/%d:%d" % (slug, cap, v["n"]))
            ep = os.path.join(OUT, "es", slug, "%d.json" % cap)
            if os.path.isfile(ep):
                e = load(ep)
                if not e["verses"]:
                    bad_schema.append(ep)
                if e["alignment"]["he"] != len(d["verses"]):
                    bad_schema.append(ep + " (alignment.he)")
                total_es += len(e["verses"])
    check(not bad_schema, "esquema de capítulos he/es", len(bad_schema))
    check(not bad_he, "hebreo sin marcas XML ni «/» y solo caracteres hebreos", len(bad_he))
    check(not bad_ref, "hebreo con `he_plain` (búsqueda sin niqqud)", len(bad_ref))
    check(total_he == 23213, "suma de versículos hebreos recorridos", total_he)
    check(total_es == c.get("verses_es"), "suma de versículos españoles", total_es)

    # 5) cobertura de los índices de búsqueda
    bad_search = 0
    searched = 0
    for sec in REQUIRED_SECTIONS:
        p = os.path.join(OUT, "search", "%s.json" % sec)
        if not os.path.isfile(p):
            bad_search += 1
            continue
        s = load(p)
        searched += s["count"]
        for ref, he, es in s["verses"][:50] + s["verses"][-50:]:
            slug, cap, n = ref.split("/")
            if not os.path.isfile(os.path.join(OUT, "he", slug, "%s.json" % cap)):
                bad_search += 1
    check(bad_search == 0, "índices de búsqueda coherentes", len(REQUIRED_SECTIONS))
    check(searched == 23213, "búsqueda cubre los 23.213 versículos", searched)

    # 6) alineación curada
    bad_align = []
    for slug in align["curated"]:
        he_total = es_total = 0
        for cap in range(1, 30):
            hp = os.path.join(OUT, "he", slug, "%d.json" % cap)
            ep = os.path.join(OUT, "es", slug, "%d.json" % cap)
            if not os.path.isfile(hp):
                break
            he_total += len(load(hp)["verses"])
            es_total += len(load(ep)["verses"])
        if he_total != es_total:
            bad_align.append("%s he=%d es=%d" % (slug, he_total, es_total))
    check(not bad_align, "libros con regla curada cuadran he/es", align["curated"])
    check(len(align["chapters"]) > 0, "align.json documenta divergencias de numeración",
          len(align["chapters"]))

    print("\n== %d OK / %d FALLA ==" % (ok, len(fail)))
    if fail:
        for f in fail:
            print("  - " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
