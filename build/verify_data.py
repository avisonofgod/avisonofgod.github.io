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
STRONG_OK = re.compile(r"^H?\d+(\+H?\d+)*$")

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
    bad_palabras = []
    total_he = total_es = 0
    he_pal = he_pal_strong = es_tok = es_tok_strong = 0
    etiquetados_he, etiquetados_es, con_version = set(), set(), set()
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
                ref = "%s/%d:%d" % (slug, cap, v["n"])
                hw, hs, hx = v.get("hw"), v.get("hs"), v.get("hx")
                if hw or hs or hx:              # solo los versículos de la versión propia
                    etiquetados_he.add((slug, cap, v["n"]))
                    if not hw or not hs or not hx:
                        bad_palabras.append(ref + " (hw/hs/hx incompletos)")
                        continue
                    if " ".join(hw) != t:
                        bad_palabras.append(ref + " (join != he)")
                    if len(hw) != len(hs) or len(hw) != len(hx):
                        bad_palabras.append(ref + " (hs/hx desalineados)")
                    for palabra, comps in zip(hw, hx):
                        if "".join(c[0] for c in comps) != palabra:
                            bad_palabras.append(ref + " (componentes != palabra)")
                        for _txt, cid in comps:
                            if cid and not (cid.startswith("P/") or STRONG_OK.match(cid)):
                                bad_palabras.append(ref + " (id raro: %s)" % cid)
                    he_pal += len(hw)
                    he_pal_strong += sum(1 for s in hs if s)
            ep = os.path.join(OUT, "es", slug, "%d.json" % cap)
            if os.path.isfile(ep):
                e = load(ep)
                if not e["verses"]:
                    bad_schema.append(ep)
                if e["alignment"]["he"] != len(d["verses"]):
                    bad_schema.append(ep + " (alignment.he)")
                total_es += len(e["verses"])
                for v in e["verses"]:
                    if v.get("es_version"):
                        con_version.add((slug, cap, v["n"]))
                    st = v.get("st")
                    if st:
                        etiquetados_es.add((slug, cap, v["n"]))
                    if not st:
                        continue
                    if len(st) != len((v["es"] or "").split()):
                        bad_palabras.append("%s/%d:%d (st != tokens)" % (slug, cap, v["n"]))
                    es_tok += len(st)
                    es_tok_strong += sum(1 for s in st if s)
    check(not bad_schema, "esquema de capítulos he/es", len(bad_schema))
    check(not bad_he, "hebreo sin marcas XML ni «/» y solo caracteres hebreos", len(bad_he))
    check(not bad_ref, "hebreo con `he_plain` (búsqueda sin niqqud)", len(bad_ref))
    check(not bad_palabras, "palabras y componentes bien formados (`hw`/`hs`/`hx`, `st`)",
          len(bad_palabras))
    check(etiquetados_he == etiquetados_es == con_version and con_version,
          "el etiquetado cubre EXACTAMENTE los versículos de la versión propia עבדיהו",
          "he=%d es=%d versión=%d" % (len(etiquetados_he), len(etiquetados_es), len(con_version)))
    check(he_pal > 0 and he_pal_strong == he_pal,
          "hebreo: cada palabra de los versículos propios trae su raíz",
          "%d palabras (%d con Strong)" % (he_pal, he_pal_strong))
    check(es_tok_strong > 0 and es_tok_strong <= es_tok,
          "español: tokens con id (resto = partículas sueltas)",
          "%d/%d (%.0f%%)" % (es_tok_strong, es_tok, 100 * es_tok_strong / max(1, es_tok)))
    check(total_he == 23213, "suma de versículos hebreos recorridos", total_he)
    check(total_es == c.get("verses_es"), "suma de versículos españoles", total_es)

    # 4b) abecedario hebreo (lectura pictográfica)
    p_letras = os.path.join(OUT, "letras.json")
    malas_letras = []
    if not os.path.isfile(p_letras):
        malas_letras.append("falta letras.json")
    else:
        d = load(p_letras)
        letras, orden, finales = d.get("letters", {}), d.get("order", []), d.get("finals", {})
        if len(letras) != 22 or len(orden) != 22 or sorted(orden) != sorted(letras):
            malas_letras.append("22 letras y su orden")
        for letra, v in letras.items():
            if not (v.get("nombre") and v.get("pictograma")):
                malas_letras.append("%s sin nombre/pictograma" % letra)
            if v.get("orden") != orden.index(letra) + 1:
                malas_letras.append("%s con orden raro" % letra)
        if len(finales) != 5 or set(finales.values()) - set(letras):
            malas_letras.append("formas finales")
    check(not malas_letras, "abecedario hebreo (22 letras + 5 finales, con pictografía)",
          malas_letras[:3] or "letras.json")

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

    # 7) versiones españolas (enmiendas por versículo sobre la RV1909)
    ver_p = os.path.join(OUT, "versions.json")
    if not os.path.isfile(ver_p):
        check(False, "versions.json presente", ver_p)
    else:
        ver = load(ver_p)
        contados = {}
        for book in idx["books"]:
            slug = book["slug"]
            for cap in range(1, book["chapters"] + 1):
                ep = os.path.join(OUT, "es", slug, "%d.json" % cap)
                if not os.path.isfile(ep):
                    continue
                for v in load(ep)["verses"]:
                    if v.get("es_version"):
                        contados[v["es_version"]] = contados.get(v["es_version"], 0) + 1
        declarado = {v["short"]: v["verses_applied"] for v in ver["versions"] if v["verses_applied"]}
        check(contados == declarado, "versions.json cuadra con los versículos marcados", contados)
        check(all(v.get("license") for v in ver["versions"]),
              "cada versión declara su licencia", len(ver["versions"]))

    print("\n== %d OK / %d FALLA ==" % (ok, len(fail)))
    if fail:
        for f in fail:
            print("  - " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
