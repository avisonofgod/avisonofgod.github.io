"""Casos en los que la división por CAPÍTULOS no coincide entre el Tanaj y la RV1909.

Solo dos libros parten el contenido en capítulos distintos (el resto de las diferencias son
de ±1 versículo dentro del mismo capítulo y no cambian el texto):

- **Yoel**: el Tanaj tiene 4 capítulos; la RV1909 tiene 3.
  Yoel 1↔1 · Yoel 2↔2 (v1-27) · Yoel 3↔2 (v28-32) · Yoel 4↔3.
- **Malaquías**: el Tanaj tiene 3 capítulos; la RV1909 tiene 4.
  Mal 1↔1 · Mal 2↔2 · Mal 3↔3 (v1-18) + 4 (v1-6).

Cada entrada: slug → {capítulo_hebreo: [(capítulo_es, versículo_inicial_es, n_versículos)]}.
El build escribe el español EN el espacio del hebreo y guarda `es_ref` con la cita original
de la RV1909, de modo que nada se falsea y todo se puede citar.
"""

CURATED = {
    "yoel": {
        1: [(1, 1, 20)],
        2: [(2, 1, 27)],
        3: [(2, 28, 5)],
        4: [(3, 1, 21)],
    },
    "malakhi": {
        1: [(1, 1, 14)],
        2: [(2, 1, 17)],
        3: [(3, 1, 18), (4, 1, 6)],
    },
}


def slice_es(es_chaps, slug, he_chapter):
    """Devuelve [(n_hebreo, texto_es, cita_es)] para un capítulo hebreo, o None.

    `None` = sin regla curada (el build usa la numeración propia del español).
    """
    rule = CURATED.get(slug, {}).get(he_chapter)
    if not rule:
        return None
    out = []
    n = 0
    for cap, start, count in rule:
        verses = es_chaps.get(cap) or []
        by_n = {v["n"]: v["es"] for v in verses}
        for i in range(start, start + count):
            n += 1
            out.append((n, by_n.get(i, ""), "%d:%d" % (cap, i)))
    return out
