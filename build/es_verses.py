"""Enmiendas de TEXTO en español sobre la RV1909 (data/valera.json no se versiona).

`data/valera.json` se baja de getbible v2 y NO se versiona, así que cualquier
corrección de texto debe vivir aquí para que el build sea reproducible:

    OVERRIDES = {slug: {(capítulo, versículo): "texto final"}}

El texto sustituye al de la RV1909 al generar v1/es/. Se anota en
`es_override` dentro del versículo para no falsear la cita de la fuente.
"""

OVERRIDES = {
    "bereshit": {
        (1, 1): "En el principio creó Elohim los cielos y la tierra.",
    },
}


def apply(es_chaps, slug):
    """Sustituye in situ el texto español de (capítulo, versículo) según OVERRIDES."""
    reglas = OVERRIDES.get(slug)
    if not reglas:
        return
    for cap, versos in es_chaps.items():
        for v in versos:
            nuevo = reglas.get((cap, v["n"]))
            if nuevo is not None:
                v["es"] = nuevo
                v["es_override"] = True
