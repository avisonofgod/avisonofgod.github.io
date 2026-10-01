#!/usr/bin/env python3
"""Convierte un archivo del usuario en una capa de versión española (build/es_versions/).

Sirve para meter una traducción completa (o un tramo) SIN tocar data/valera.json:
el resultado es un JSON versionado que el build aplica versículo a versículo y
etiqueta con `es_version`.

Entrada admitida (se elige por extensión):
  .json           formato de capa: {"version","short","source","license","books":{slug:{cap:{v:texto}}}}
  .tsv/.csv/.txt  una línea por versículo:  <referencia><TAB|;|,>texto   (el texto puede seguir en más líneas)
  .md             igual que .txt (se ignoran las líneas sin referencia)
  .pdf            se extrae con pdftotext -layout y se parsea igual
  .docx           se lee word/document.xml (stdlib) y se parsea igual
  .epub           se leen los XHTML del spine (stdlib) y se parsea igual

La referencia puede escribirse como quieras: "Génesis 1:1", "Bereshit 1:1",
"Gen 1:1", "בְּרֵאשִׁית 1:1"… se resuelve con build/slugs.py (slug, alias, es/en/he,
nombre de la RV1909). Se valida contra v1/he/ y se reporta cobertura y huecos.

Uso:
  python3 build/import_es_version.py --in revision.pdf --version "1.0" --short v1.0 \
      --author Obadias --source "Revisión de Obadias sobre la RV1909" \
      --license "CC0 1.0 Universal" --spdx CC0-1.0 \
      --out build/es_versions/obadias-v1.0.json [--merge] [--dry-run]
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)

import slugs  # noqa: E402

# "Génesis 1:1  texto…" / "1 Reyes 2,3" / "Sal 23.1" (nombre sin dígitos)
REF = re.compile(r"^\s*([1-3]?\s*[^\d:;,\t]{2,28}?)\s+(\d{1,3})\s*[:.,]\s*(\d{1,3})\s*[:-]?\s*(.*)$")


def _texto_plano(t):
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?s)<br\s*/?>|</p>|</div>|</li>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    return t


def leer_pdf(path):
    try:
        out = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", path, "-"],
                             capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        sys.exit("no pude extraer texto del PDF (%s); ¿tiene capa de texto? usa OCR antes" % e)
    return out.stdout.decode("utf-8", "replace")


def leer_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"(?s)</w:p>", "\n", xml)
    return _texto_plano(xml)


def leer_epub(path):
    partes = []
    with zipfile.ZipFile(path) as z:
        nombres = [n for n in z.namelist() if re.search(r"\.(x?html?|xhtml)$", n, re.I)]
        for n in sorted(nombres):
            partes.append(_texto_plano(z.read(n).decode("utf-8", "replace")))
    return "\n".join(partes)


def leer_texto(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def parsear_versos(texto):
    """Líneas "referencia + texto" -> {(slug, cap, n): texto}.

    El texto puede continuar en las líneas siguientes (se acumula hasta la
    próxima referencia). Devuelve también la lista de referencias no resueltas.
    """
    versos = {}
    malas = []
    actual = None
    for linea in texto.splitlines():
        linea = " ".join(linea.split())
        if not linea:
            continue
        m = REF.match(linea)
        if not m:
            if actual:
                s, c, n = actual
                versos[(s, c, n)] = (versos[(s, c, n)] + " " + linea).strip()
            continue
        libro, cap, n, resto = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        slug = slugs.resolve(libro) or _por_rv1909(libro)
        if not slug:
            malas.append(linea[:60])
            actual = None
            continue
        actual = (slug, cap, n)
        versos[actual] = (versos.get(actual, "") + " " + resto).strip()
    return versos, malas


def _por_rv1909(nombre):
    clave = " ".join(nombre.split()).lower()
    for b in slugs.BOOKS:
        if str(b.get("rv1909") or "").lower() == clave:
            return b["slug"]
    return None


def leer_versiones(out_dir):
    """v1/he/ -> {(slug, cap, n)} para validar cobertura."""
    existen = set()
    for b in slugs.BOOKS:
        d = os.path.join(out_dir, "he", b["slug"])
        if not os.path.isdir(d):
            continue
        for archivo in sorted(os.listdir(d)):
            if not archivo.endswith(".json"):
                continue
            cap = int(archivo[:-5])
            with open(os.path.join(d, archivo), encoding="utf-8") as fh:
                for v in json.load(fh)["verses"]:
                    existen.add((b["slug"], cap, v["n"]))
    return existen


def main():
    ap = argparse.ArgumentParser(description="Importa una versión española a build/es_versions/")
    ap.add_argument("--in", dest="entrada", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--short", default=None)
    ap.add_argument("--author", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--license", default="")
    ap.add_argument("--spdx", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--out-json", default=os.path.join(RAIZ, "v1"), help="v1/ para validar cobertura")
    ap.add_argument("--merge", action="store_true", help="fusiona con el --out existente")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    ext = os.path.splitext(a.entrada)[1].lower()
    if ext == ".json":
        with open(a.entrada, encoding="utf-8") as fh:
            capa = json.load(fh)
        capa.setdefault("version", a.version)
        capa.setdefault("short", a.short or a.version)
        libros = {}
        for slug, caps in (capa.get("books") or {}).items():
            if slugs.resolve(slug) is None:
                sys.exit("libro desconocido en el JSON: %s" % slug)
            for cap, vers in caps.items():
                for n, txt in vers.items():
                    libros.setdefault(slug, {}).setdefault(str(int(cap)), {})[str(int(n))] = " ".join(str(txt).split())
        capa["books"] = libros
        n_versos = sum(len(v) for c in libros.values() for v in c.values())
    else:
        lector = {"pdf": leer_pdf, "docx": leer_docx, "epub": leer_epub}.get(ext.lstrip("."), leer_texto)
        texto = lector(a.entrada)
        versos, malas = parsear_versos(texto)
        if malas:
            print("AVISO: %d líneas con referencia no reconocida; primeras: %s"
                  % (len(malas), "; ".join(malas[:3])))
        if not versos:
            sys.exit("no encontré ninguna referencia de versículo en %s" % a.entrada)
        libros = {}
        for (slug, cap, n), txt in sorted(versos.items()):
            libros.setdefault(slug, {}).setdefault(str(cap), {})[str(n)] = txt
        capa = {"version": a.version, "short": a.short or a.version, "author": a.author,
                "source": a.source, "license": a.license, "spdx": a.spdx, "note": a.note}
        n_versos = len(versos)

    if a.merge and os.path.isfile(a.out):
        with open(a.out, encoding="utf-8") as fh:
            prev = json.load(fh)
        for slug, caps in prev.get("books", {}).items():
            for cap, vers in caps.items():
                for n, txt in vers.items():
                    libros.setdefault(slug, {}).setdefault(str(cap), {}).setdefault(str(n), txt)
        capa["version"] = prev.get("version", capa["version"])
        capa["source"] = prev.get("source", capa["source"])
        capa["license"] = prev.get("license", capa["license"])
    # cobertura contra el hebreo ya construido
    existen = leer_versiones(a.out_json)
    faltan = []
    if existen:
        for slug, caps in libros.items():
            for cap, vers in caps.items():
                for n in vers:
                    if (slug, int(cap), int(n)) not in existen:
                        faltan.append((slug, cap, n))
        # el build solo aplica lo que existe en el hebreo: no se escribe lo inalcanzable
        for slug, cap, n in faltan:
            libros.get(slug, {}).get(cap, {}).pop(n, None)
        libros = {s: {c: v for c, v in caps.items() if v} for s, caps in libros.items()}
        libros = {s: c for s, c in libros.items() if c}
        n_versos -= len(faltan)
    capa["books"] = libros

    print("version      : %s (%s)" % (capa.get("version"), capa.get("short")))
    print("libros       : %d" % len(libros))
    print("versiculos   : %d" % n_versos)
    if existen:
        print("sin hebreo   : %d%s" % (len(faltan), (" -> " + ", ".join("%s %s:%s" % f for f in sorted(faltan)[:5])) if faltan else ""))
    else:
        print("sin hebreo   : no hay %s/he/ (salta la validación)" % a.out_json)
    print("archivo      : %s" % a.out)

    if a.dry_run:
        print("(--dry-run: no se escribió nada)")
        return 1 if faltan else 0

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(capa, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("escrito      : %s (%d bytes)" % (a.out, os.path.getsize(a.out)))
    return 1 if faltan else 0


if __name__ == "__main__":
    sys.exit(main())
