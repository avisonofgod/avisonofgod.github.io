"""Relación palabra hebrea <-> traducción, SOLO para la versión propia עבדיהו (v1.0).

Regla
-----
El resaltado no es global: existe únicamente en los versículos que la capa propia
(`build/es_versions/עבדיהו-v1.0.json`, autor עבדיהו, CC0-1.0) ha reescrito. El resto de la
API (RV1909 tal cual) va sin etiquetas y el lector no ofrece marcador ahí.

Qué se publica por versículo (lo consume el lector)
---------------------------------------------------
    hw  palabras hebreas, en el orden del texto servido (" ".join(hw) == he)
    hs  Strong de la RAÍZ de cada palabra (o None si no tiene)
    hx  componentes de cada palabra: [[["בְּ","P/b"],["רֵאשִׁ֖ית","H7225"]], ...]
        - prefijo/partícula -> id "P/<letra del lemma>" (tabla PREFIJOS)
        - raíz -> su número de Strong ("H7225")
    st  id por token español (paralelo a `es.split(" ")`); None = palabra española que no
        se une a ninguna palabra hebrea (se deja sin marcar)

Cómo se empareja
----------------
1. Raíces: puente Strong con la RV1865 etiquetada (CC0, pin en fetch_sources.sh):
   aciertos exactos monótonos -> moda del desplazamiento -> asignación por posición.
2. Prefijos: cada prefijo toma el token español libre que va DELANTE de su raíz y que
   pertenece a su clase (artículo -> el/la/los/las; waw -> y/pero/…; preposición ->
   en/con/por/…). Si no hay token de su clase, quedan sin pareja: "deja las partículas
   que no se unan a ninguna".
   Ejemplo (Bereshit 1:1): בְּרֵאשִׁית -> בְּ = «En» (P/b) y רֵאשִׁית = «principio» (H7225);
   el artículo suelto «el» no se une a nadie y no se marca.

Uso
    python3 build/strong_es.py           # versículos de la capa עבדיהו
    python3 build/strong_es.py --dry
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
import es_verses                                 # noqa: E402
import slugs                                     # noqa: E402
import wlc                                       # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTOR = "עבדיהו"
SALIDA = os.path.join(RAIZ, "build", "es_strong", "%s-v1.0-strong.json" % AUTOR)
RV1865_DIR = os.path.join(RAIZ, "data", "rv1865_strongs")

META = {
    "version": "1.0",
    "short": "v1.0",
    "author": AUTOR,
    "license": "CC0 1.0 Universal (dedicación al dominio público)",
    "spdx": "CC0-1.0",
    "source": ("Relación palabra hebrea <-> traducción sobre la versión propia (texto base "
               "Reina-Valera 1909, dominio público). Raíces por puente Strong con la RV1865 "
               "etiquetada (ohneklavier-creator/reina-valera-1865-strongs-concordancia, "
               "CC0-1.0); componentes hebreos del WLC (openscriptures/morphhb, CC BY 4.0)."),
    "scope": "solo los versículos de la capa build/es_versions/%s-v1.0.json" % AUTOR,
    "note": ("`hx` separa los prefijos de la raíz hebrea; `st` da el id por palabra "
             "española. Los id «P/<letra>» son los códigos de prefijo del WLC (morphhb) y "
             "no son números de Strong propios."),
}

# Códigos de prefijo del WLC (morphhb) -> letra hebrea, glosa y clase de palabras
# españolas que pueden ocuparlo. Tabla propia, comprobada contra `morph` del propio XML
# (c=ו HC…, d=ה HTd… artículo, i=ה HTi… interrogativa, b/l/m/k preposiciones, s=ש HTr…).
PREFIJOS = {
    "c": {"he": "ו", "glosa": "y, pero, ni… (conjunción)",
          "clase": ["y", "e", "pero", "mas", "sino", "ni", "entonces", "asi", "tambien", "aun"]},
    "d": {"he": "ה", "glosa": "el, la, los, las (artículo)",
          "clase": ["el", "la", "los", "las", "lo"]},
    "i": {"he": "ה", "glosa": "interrogativa (¿?)", "clase": []},
    "b": {"he": "ב", "glosa": "en, con, por (preposición)",
          "clase": ["en", "con", "por", "de", "a", "entre", "contra", "sobre", "segun", "para"]},
    "l": {"he": "ל", "glosa": "a, para (preposición)",
          "clase": ["a", "al", "para", "por", "de", "en", "hacia"]},
    "k": {"he": "כ", "glosa": "como (comparativo)", "clase": ["como", "cual", "segun"]},
    "m": {"he": "מ", "glosa": "de, desde (preposición)",
          "clase": ["de", "desde", "entre", "sin", "mas", "fuera"]},
    "s": {"he": "ש", "glosa": "que (relativo)", "clase": ["que", "lo", "cual"]},
}

STRONG_RE = re.compile(r"[HG]\d+")          # números de Strong ya etiquetados (H7225)
LEMMA_NUM = re.compile(r"\d+")              # raíz dentro del `lemma` del WLC ("b/7225")
CONSONANTE = re.compile(r"[\u05d0-\u05ea]")
ACCENT = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def norm(txt):
    """Minúsculas, sin acentos, sin puntuación: para cotejar etiquetas con tokens."""
    t = unicodedata.normalize("NFD", (txt or "").lower()).translate(ACCENT)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "".join(c for c in t if c.isalnum())


def partir_palabra(palabra, lemma):
    """[(texto, id), ...] de una palabra hebrea: prefijos (P/<letra>) + raíz (H####).

    El número de prefijos sale del `lemma` del WLC ("b/7225" -> uno; "c/d/776" -> dos).
    Si el texto no tiene consonantes suficientes, la palabra queda entera con su raíz.
    """
    partes = (lemma or "").split("/")
    codigos = [re.findall(r"[a-z]+", p) for p in partes[:-1]] if len(partes) > 1 else []
    raiz = LEMMA_NUM.findall(partes[-1]) if partes else []
    raiz = "H" + raiz[-1] if raiz else None
    cortes = len(codigos)
    letras = [i for i, ch in enumerate(palabra) if CONSONANTE.match(ch)]
    if cortes == 0 or len(letras) < cortes + 1:
        return [(palabra, raiz)]
    idx = [letras[k] for k in range(cortes + 1)] + [len(palabra)]
    comps = []
    for k in range(cortes):
        comps.append((palabra[idx[k]:idx[k + 1]], "P/" + codigos[k][0]))
    comps.append((palabra[idx[cortes]:], raiz))
    return comps


def he_analisis(chapter_body):
    """[(palabra, Strong de la raíz, [(componente, id), …])] + marcas de párrafo.

    Une el maqqef con la MISMA regla que `wlc.extract_verse` (wlc.grupos_maqqef), así las
    palabras coinciden exactamente con el texto servido.
    """
    crudas, marcas = wlc.tokens_con_lemma(wlc.NOTE_RE.sub(" ", chapter_body))
    salida = []
    for grupo in wlc.grupos_maqqef(crudas):   # len(salida) = índice de la palabra
        texto = "".join(crudas[i][0] for i in grupo)
        fuertes = [f for i in grupo for f in (crudas[i][1] or "").split("+") if f]
        comps = []
        for i in grupo:
            comps.extend(partir_palabra(crudas[i][0], crudas[i][2]))
        # id único por aparición: "P/d#4" (artículo) y "H776#4" (raíz de la palabra 4). Así
        # tocar «los» marca ESE artículo y tocar «sobre» (dos veces en el versículo) marca solo
        # el suyo.
        comps = [(unicodedata.normalize("NFC", t),
                  ("%s#%d" % (cid, len(salida)) if cid else cid)) for t, cid in comps]
        unida = "+".join(dict.fromkeys(fuertes)) or None
        salida.append((unicodedata.normalize("NFC", texto), unida, comps))
    return salida, "".join(marcas)


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


def etiquetar_raices(tokens, filas):
    """[Strong|None] por token español (solo raíces). Devuelve (etiquetas, exactos, asignados)."""
    etiquetas = [None] * len(tokens)
    normas = [norm(t) for t in tokens]
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
    asignados = 0
    for pos, palabra, st in filas:
        objetivo = pos + offset
        if 0 <= objetivo < len(tokens) and etiquetas[objetivo] is None:
            etiquetas[objetivo] = st
            asignados += 1
            continue
        for d in (1, -1, 2, -2, 3, -3):
            j = objetivo + d
            if 0 <= j < len(tokens) and etiquetas[j] is None:
                etiquetas[j] = st
                asignados += 1
                break
    return etiquetas, exactos, asignados


def etiquetar_automatico(analisis, tokens, filas):
    """Puente Strong (versículos sin mapa del autor): raíces por posición y prefijos por clase.

    Las etiquetas se convierten a ids por aparición ("H776#4"), igual que `hx`, para que el
    lector no marque dos veces la misma raíz cuando aparece repetida en el versículo.
    """
    planas, exactos, asignados = etiquetar_raices(tokens, filas)
    cola = {}
    for _txt, _strong, comps in analisis:
        for _ct, cid in comps:
            if cid and cid.startswith("H"):
                cola.setdefault(cid.split("#")[0], []).append(cid)
    etiquetas = []
    for e in planas:
        if e and e.startswith("H") and cola.get(e):
            etiquetas.append(cola[e].pop(0))
        else:
            etiquetas.append(e)
    for _txt, _strong, comps in analisis:          # prefijos: delante de su raíz, por clase
        raices = [cid for _ct, cid in comps if cid and cid.startswith("H")]
        if not raices:
            continue
        pos = next((j for j, e in enumerate(etiquetas) if e in raices), None)
        if pos is None:
            continue
        inicio = max((j for j in range(pos) if etiquetas[j] is not None), default=-1)
        huecos = [j for j in range(inicio + 1, pos) if etiquetas[j] is None]
        for _ct, cid in comps:
            if not (cid and cid.startswith("P/")):
                continue
            clase = PREFIJOS.get(cid.split("#")[0][2:], {}).get("clase", [])
            elegido = next((j for j in huecos if norm(tokens[j]) in clase), None)
            if elegido is None:
                continue
            etiquetas[elegido] = cid
            huecos.remove(elegido)
    return etiquetas, exactos, asignados


def etiquetar_por_glosas(analisis, tokens, glosas):
    """`st` a partir del mapa del autor (glosas), sin adivinar por posición.

    `glosas` = una lista por palabra hebrea, y cada palabra es {id del componente: [tokens]}.
    Se da por id (no por orden) para poder traducir en orden español aunque el hebreo vaya al
    revés: en `מִתַּחַת` los tokens «debajo» (H8478#7) y «de» (P/m#7) pueden ir en ese orden.
    Los tokens de cada palabra se buscan en el texto en el orden del mapa.
    Devuelve (etiquetas, nº de tokens colocados) o None si el mapa no cuadra con el texto servido.
    """
    if len(glosas) != len(analisis):
        return None
    etiquetas = [None] * len(tokens)
    normas = [norm(t) for t in tokens]
    cursor = colocados = 0
    for i, (_txt, _strong, comps) in enumerate(analisis):
        mapa = glosas[i]
        if not isinstance(mapa, dict):
            return None
        propios = {cid for _t, cid in comps if cid}
        if set(mapa) - propios:                # id que no pertenece a esta palabra
            return None
        for cid, grupo in mapa.items():
            for palabra in grupo or []:
                pn = norm(palabra)
                j = next((x for x in range(cursor, len(tokens)) if normas[x] == pn), -1)
                if j < 0:
                    return None          # el mapa no corresponde al texto actual
                etiquetas[j] = cid
                cursor = j + 1
                colocados += 1
    return etiquetas, colocados


def analizar_versiculo(cuerpo, tokens, cita, tags, slug, cap, n, glosas=None):
    """{"hw","hs","hx","st"} de un versículo, o None si falta la fuente etiquetada."""
    analisis, _marcas = he_analisis(cuerpo)
    filas = tags.get(slug, {}).get(cap, {}).get(n)
    if filas is None and cita:                  # libro curado: la cita usa otra numeración
        try:
            c2, n2 = (int(x) for x in str(cita).split(":"))
            filas = tags.get(slug, {}).get(c2, {}).get(n2)
        except (TypeError, ValueError):
            filas = None
    filas = filas or []
    if glosas:
        # mapa del autor: manda sobre el puente Strong y no reparte partículas sueltas
        por_glosas = etiquetar_por_glosas(analisis, tokens, glosas)
        if por_glosas is not None:
            etiquetas, colocados = por_glosas
            exactos, asignados = colocados, colocados
            return {
                "hw": [t for t, _s, _c in analisis],
                "hs": [s for _t, s, _c in analisis],
                "hx": [[[ct, cid] for ct, cid in comps] for _t, _s, comps in analisis],
                "st": etiquetas,
            }, len(filas), exactos, asignados, True
    etiquetas, exactos, asignados = etiquetar_automatico(analisis, tokens, filas)
    return {
        "hw": [t for t, _s, _c in analisis],
        "hs": [s for _t, s, _c in analisis],
        "hx": [[[ct, cid] for ct, cid in comps] for _t, _s, comps in analisis],
        "st": etiquetas,
    }, len(filas), exactos, asignados, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wlc", default=os.path.join(RAIZ, "data", "morphhb", "wlc"))
    ap.add_argument("--valera", default=os.path.join(RAIZ, "data", "valera.json"))
    ap.add_argument("--out", default=SALIDA)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(RV1865_DIR):
        sys.exit("falta %s (bash build/fetch_sources.sh)" % RV1865_DIR)
    capas = es_verses.load()
    cubiertos, por_glosas = set(), {}
    for capa in capas:                          # SOLO los versículos de la versión propia
        cubiertos.update(capa["verses"].keys())
        por_glosas.update(capa.get("glosas") or {})
    textos = build_data.textos_es(capas, args.valera, args.wlc)
    tags = etiquetas_rv1865()

    stats = Counter()
    libros = {}
    for slug, cap, n in sorted(cubiertos):
        xml = os.path.join(args.wlc, slugs.BY_SLUG[slug]["osis"] + ".xml")
        cuerpo = build_data.cuerpo_versiculo(xml, cap, n)
        if cuerpo is None:
            stats["sin_hebreo"] += 1
            continue
        txt, cita = textos.get((slug, cap, n), (None, None))
        if txt is None:
            stats["sin_es"] += 1
            continue
        tokens = txt.split()
        bloque, n_filas, exactos, asignados, con_glosas = analizar_versiculo(
            cuerpo, tokens, cita, tags, slug, cap, n,
            glosas=por_glosas.get((slug, cap, n)))
        libros.setdefault(slug, {}).setdefault(cap, {})[n] = bloque
        stats["versiculos"] += 1
        stats["con_glosas"] += 1 if con_glosas else 0
        stats["tokens"] += len(tokens)
        stats["tokens_etiquetados"] += sum(1 for e in bloque["st"] if e)
        stats["palabras"] += len(bloque["hw"])
        stats["componentes"] += sum(len(c) for c in bloque["hx"])
        stats["etiquetas_fuente"] += n_filas
        stats["aciertos_exactos"] += exactos
        stats["raices_emparejadas"] += asignados
        if not n_filas:
            stats["versiculos_sin_fuente"] += 1

    payload = dict(META, prefijos=PREFIJOS, stats=dict(stats), books=libros)
    if args.dry:
        print("(dry) versículos=%d" % stats["versiculos"])
    else:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with open(args.out, "wb") as fh:
            fh.write(blob)
        print("escrito %s (%.1f KB)" % (args.out, len(blob) / 1024))

    print("autor %s | versículos %d | palabras %d | componentes %d"
          % (AUTOR, stats["versiculos"], stats["palabras"], stats["componentes"]))
    print("tokens ES %d | con id %d (%.1f%%) | raíces emparejadas %d | sin fuente %d"
          % (stats["tokens"], stats["tokens_etiquetados"],
             100 * stats["tokens_etiquetados"] / max(1, stats["tokens"]),
             stats["raices_emparejadas"], stats["versiculos_sin_fuente"]))


if __name__ == "__main__":
    main()
