"""Versiones en español que se sobreponen a la RV1909.

`data/valera.json` se baja de getbible v2 y NO se versiona, así que cualquier
texto en español distinto (o corregido) vive en `build/es_versions/*.json`, que
sí se versiona. Así el build es reproducible: mismas fuentes -> mismo v1/.

Formato de cada archivo (`build/es_versions/<nombre>.json`):

    {
      "version": "Moisés Katznelson",      # nombre completo, va en v1/versions.json
      "short": "Katznelson",               # etiqueta corta, va por versículo (es_version)
      "source": "…",                       # cita bibliográfica
      "license": "…",                      # condiciones de uso / derechos
      "note": "…",                         # opcional
      "books": {"bereshit": {"1": {"1": "texto", "2": "texto"}}}
    }

Reglas del build:
  * la capa se aplica sobre el texto de la RV1909 ya alineado al capítulo hebreo;
  * el versículo tocado conserva `es` pero gana `es_version` (etiqueta corta), de
    modo que nada se falsea y se ve de dónde viene cada línea;
  * si dos archivos tocan el mismo versículo, gana el último en orden alfabético;
  * un versículo que no existe en el capítulo hebreo se ignora (y se reporta).

Para generar una capa desde un archivo del usuario (PDF/EPUB/DOCX/CSV/JSON):
    python3 build/import_es_version.py --help
"""

import json
import os

import slugs

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "es_versions")


def load(dirpath=None):
    """Lee las capas de es_versions/ en orden alfabético (la última gana).

    Devuelve [{"path", "version", "short", "source", "license", "verses": {(slug, cap, n): texto}}].
    """
    raiz = dirpath or DIR
    capas = []
    if not os.path.isdir(raiz):
        return capas
    for nombre in sorted(os.listdir(raiz)):
        if not nombre.endswith(".json"):
            continue
        ruta = os.path.join(raiz, nombre)
        try:
            with open(ruta, encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            print("AVISO: capa ilegible, se ignora %s (%s)" % (ruta, e))
            continue
        if not isinstance(raw, dict) or not isinstance(raw.get("books"), dict):
            print("AVISO: %s no tiene el formato de capa (clave `books`), se ignora" % ruta)
            continue
        versos = {}
        for slug, caps in (raw.get("books") or {}).items():
            if slug not in slugs.BY_SLUG:
                print("AVISO: %s usa un libro desconocido: %s (se ignora)" % (ruta, slug))
                continue
            for cap, vers in caps.items():
                for n, texto in vers.items():
                    texto = " ".join(str(texto).split())
                    if texto:
                        versos[(slug, int(cap), int(n))] = texto
        capas.append({
            "path": ruta,
            "file": nombre,
            "version": raw.get("version") or nombre[:-5],
            "short": raw.get("short") or raw.get("version") or nombre[:-5],
            "source": raw.get("source") or "",
            "license": raw.get("license") or "",
            "note": raw.get("note") or "",
            "verses": versos,
        })
    return capas


def apply(es_chaps, slug, capas=None):
    """Sustituye in situ el texto español de es_chaps[cap][i] según las capas.

    Marca `es_version` con la etiqueta corta de la versión aplicada.
    Devuelve el nº de versículos sustituidos.
    """
    capas = capas if capas is not None else load()
    tocados = 0
    for capa in capas:
        for cap, versos in es_chaps.items():
            for v in versos:
                nuevo = capa["verses"].get((slug, cap, v["n"]))
                if nuevo is not None:
                    v["es"] = nuevo
                    v["es_version"] = capa["short"]
                    tocados += 1
    return tocados


def entries(capas=None):
    """Nº de versículos declarados por capa (sin comprobar contra el hebreo)."""
    capas = capas if capas is not None else load()
    return {c["version"]: len(c["verses"]) for c in capas}


def payload(applied, capas=None):
    """Bloque `versions` de v1/versions.json: qué capas hay y cuánto se aplicó.

    `applied` = {nombre_de_version: nº de versículos realmente escritos en v1/es}.
    """
    capas = capas if capas is not None else load()
    out = []
    for c in capas:
        out.append({
            "version": c["version"],
            "short": c["short"],
            "source": c["source"],
            "license": c["license"],
            "file": "build/es_versions/" + c["file"],
            "verses_declared": len(c["verses"]),
            "verses_applied": applied.get(c["version"], 0),
        })
    return out
