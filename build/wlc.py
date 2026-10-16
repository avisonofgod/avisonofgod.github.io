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
WORD_RE = re.compile(r'<w\b([^>]*)>(.*?)</w>', re.S)
LEMMA_RE = re.compile(r'lemma="([^"]*)"')
TOKEN_RE = re.compile(r'<w\b([^>]*)>(.*?)</w>|<seg\b[^>]*type="([^"]+)"[^>]*>(.*?)</seg>', re.S)
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


def strong_de(attrs):
    """Número de Strong principal del atributo `lemma` (p. ej. `b/7225` -> `H7225`)."""
    m = LEMMA_RE.search(attrs or "")
    nums = re.findall(r"\d+", m.group(1)) if m else []
    return "H" + nums[-1] if nums else None


def _tokens(body):
    """[(palabra, Strong|None)] y marcas de párrafo, respetando maqqef/paseq."""
    words, cur, strongs, marks = [], [], [], []

    def flush():
        if cur:
            w = "".join(cur).strip()
            if w:
                words.append((w, strongs[0] if strongs else None))
            cur.clear()
            strongs.clear()

    for m in TOKEN_RE.finditer(body):
        if m.group(1) is not None:                      # <w lemma="…">palabra</w>
            flush()
            cur.append(_text(m.group(2)).replace("/", ""))
            strongs.append(strong_de(m.group(1)))
        else:                                           # <seg type="...">…</seg>
            typ, txt = m.group(3), _text(m.group(4)).strip()
            if typ == "x-maqqef":
                cur.append(MAQQEF)
            elif typ == "x-sof-pasuq":
                cur.append(SOF_PASUQ)
            elif typ == "x-paseq":
                flush()
                words.append((PASEQ, None))
            elif typ in PARA_MARKS:
                marks.append(txt)
            elif txt:
                cur.append(txt)      # x-suspended, x-reversednun: van en el texto
    flush()
    return words, marks


def extract_verse(body, with_words=False):
    """Devuelve (texto_hebreo, marca_de_parrafo[, palabras]).

    `palabras` = [(palabra, Strong|None)] en el orden del texto; al unirlas con un
    espacio se obtiene EXACTAMENTE el texto devuelto (lo comprueba verify_data.py).
    """
    words, marks = _tokens(NOTE_RE.sub(" ", body))
    # el maqqef (־) une dos palabras en UNA sola: se fusionan y sus Strong se suman
    # ("H5921+H6440"), así « ".join(words) » reproduce exactamente el texto servido.
    unidas = []
    for w, s in words:
        if unidas and (unidas[-1][0].endswith(MAQQEF) or w.startswith(MAQQEF)):
            pw, ps = unidas[-1]
            fuertes = [f for f in dict.fromkeys((ps or "").split("+") + (s or "").split("+")) if f]
            unidas[-1] = (pw + w, "+".join(fuertes) or None)
        else:
            unidas.append((w, s))
    words = unidas
    # NFC por palabra: al unirlas con espacios se obtiene el mismo texto servido
    # (y el lector puede partir `he` por espacios y obtener exactamente `words`)
    words = [(unicodedata.normalize("NFC", w), s) for w, s in words]
    # une con el maqef: la palabra terminada en ־ se pega a la siguiente
    text = ""
    for w, _strong in words:
        if text and not text.endswith(MAQQEF) and not w.startswith(MAQQEF):
            text += " "
        text += w
    text = re.sub(r"\s+", " ", text).strip()
    # NFC: orden canónico de los signos (así el mismo versículo compara igual en JS/Go/etc.)
    text = unicodedata.normalize("NFC", text)
    if with_words:
        return text, "".join(marks), words
    return text, "".join(marks)


def parse_book(path, with_words=False):
    """Lee un archivo del WLC y devuelve {capítulo: [versículos]}.

    Cada versículo: {"n": int, "he": str, "he_plain": str, "marker": str|None}
    y, con `with_words=True`, además "words": [(palabra, Strong|None), ...] en el
    mismo orden del texto (al unirlas con espacios se obtiene "he").
    """
    with open(path, encoding="utf-8") as fh:
        xml = fh.read()
    chapters = {}
    for m in VERSE_RE.finditer(xml):
        chapter, verse = int(m.group(2)), int(m.group(3))
        fila = {"n": verse}
        if with_words:
            text, marker, words = extract_verse(m.group(4), with_words=True)
            fila["words"] = words
        else:
            text, marker = extract_verse(m.group(4))
        fila["he"] = text
        fila["he_plain"] = strip_marks(text)
        if marker:
            fila["marker"] = marker
        chapters.setdefault(chapter, []).append(fila)
    for verses in chapters.values():
        verses.sort(key=lambda v: v["n"])
    return chapters
