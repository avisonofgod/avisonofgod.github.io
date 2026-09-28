"""Lectura del WLC (Westminster Leningrad Codex) en formato OSIS de morphhb.

Reglas de extracción (comprobadas contra las marcas del propio XML):
- `<w>` es una palabra; el carácter `/` separa prefijo y raíz para la morfología y
  NO forma parte del texto → se elimina.
- `<seg type="x-maqqef">` (־) une la palabra anterior con la siguiente, sin espacio.
- `<seg type="x-sof-pasuq">` (׃) cierra el versículo, pegado a la última palabra.
- `<seg type="x-paseq">` (׀) es una pausa intermedia → palabra propia.
- `<seg type="x-pe">` (פ) y `<seg type="x-samekh">` (ס) son marcas de párrafo
  (petuĥá / setumá): no van en el texto, se reportan aparte en `marker`.
- `<note>` (notas del aparato crítico) se descarta.
"""

import re
import unicodedata

VERSE_RE = re.compile(r'<verse osisID="([^"]+?)\.(\d+)\.(\d+)">(.*?)</verse>', re.S)
TOKEN_RE = re.compile(r'<w\b[^>]*>(.*?)</w>|<seg\b[^>]*type="([^"]+)"[^>]*>(.*?)</seg>', re.S)
NOTE_RE = re.compile(r"<note\b.*?</note>", re.S)

MAQQEF = "\u05be"
SOF_PASUQ = "\u05c3"
PASEQ = "\u05c0"
PARA_MARKS = ("x-pe", "x-samekh")

# Niqqud (U+05B0-U+05BD, U+05BF, U+05C1-U+05C2, U+05C4-U+05C5, U+05C7) y te'amim
# (U+0591-U+05AF). Se eliminan solo para `he_plain`/búsqueda: el texto mostrado los conserva.
NIQQUD_RE = re.compile("[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]")
PUNCT_RE = re.compile("[\u05be\u05c0\u05c3\u05f3\u05f4]")


def strip_marks(text):
    """Hebreo sin niqqud, sin te'amim y sin puntuación (para buscar/comparar)."""
    return PUNCT_RE.sub(" ", NIQQUD_RE.sub("", text)).replace("  ", " ").strip()


def _text(fragment):
    """Texto plano de un fragmento: quita etiquetas anidadas conservando su contenido.

    Hay <w> que llevan hijos dentro (p. ej. `<seg type="x-suspended">ע</seg>r` en
    Tehilim 80:14, o la nun invertida de Bamidbar 10:35): sus letras SÍ son texto.
    """
    return re.sub(r"<[^>]+>", "", fragment or "")


def extract_verse(body):
    """Devuelve (texto_hebreo, marca_de_parrafo)."""
    body = NOTE_RE.sub(" ", body)
    words = []
    cur = []
    marks = []

    def flush():
        if cur:
            w = "".join(cur).strip()
            if w:
                words.append(w)
            cur.clear()

    for m in TOKEN_RE.finditer(body):
        if m.group(1) is not None:                      # <w>palabra</w>
            flush()
            cur.append(_text(m.group(1)).replace("/", ""))
        else:                                           # <seg type="...">…</seg>
            typ, txt = m.group(2), _text(m.group(3)).strip()
            if typ == "x-maqqef":
                cur.append(MAQQEF)
            elif typ == "x-sof-pasuq":
                cur.append(SOF_PASUQ)
            elif typ == "x-paseq":
                flush()
                words.append(PASEQ)
            elif typ in PARA_MARKS:
                marks.append(txt)
            elif txt:
                cur.append(txt)      # x-suspended, x-reversednun: van en el texto
    flush()
    # une con el maqef: la palabra terminada en ־ se pega a la siguiente
    text = ""
    for w in words:
        if text and not text.endswith(MAQQEF) and not w.startswith(MAQQEF):
            text += " "
        text += w
    text = re.sub(r"\s+", " ", text).strip()
    # NFC: orden canónico de los signos (así el mismo versículo compara igual en JS/Go/etc.)
    return unicodedata.normalize("NFC", text), "".join(marks)


def parse_book(path):
    """Lee un archivo del WLC y devuelve {capítulo: [versículos]}.

    Cada versículo: {"n": int, "he": str, "he_plain": str, "marker": str|None}
    """
    with open(path, encoding="utf-8") as fh:
        xml = fh.read()
    chapters = {}
    for m in VERSE_RE.finditer(xml):
        chapter, verse = int(m.group(2)), int(m.group(3))
        text, marker = extract_verse(m.group(4))
        chapters.setdefault(chapter, []).append({
            "n": verse,
            "he": text,
            "he_plain": strip_marks(text),
            **({"marker": marker} if marker else {}),
        })
    for verses in chapters.values():
        verses.sort(key=lambda v: v["n"])
    return chapters
