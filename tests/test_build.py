"""Pruebas del generador del Tanaj (sin red). Ejecutar: python3 -m unittest discover -s tests -v"""

# pyright: reportMissingImports=false  (los módulos de build/ se añaden al sys.path abajo)

import argparse
import json
import os
import sys
import tempfile
import unicodedata
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "build"))

import build_data                                    # noqa: E402
import curated                                       # noqa: E402
import slugs                                         # noqa: E402
import wlc                                           # noqa: E402

WLC_DIR = os.path.join(RAIZ, "data", "morphhb", "wlc")
VALERA = os.path.join(RAIZ, "data", "valera.json")


class TestParserHebreo(unittest.TestCase):
    def test_maqqef_une_palabras(self):
        cuerpo = ('<w lemma="a">עַל</w><seg type="x-maqqef">־</seg>'
                  '<w lemma="b">פְּנֵ֣י</w><seg type="x-sof-pasuq">׃</seg>')
        texto, marca = wlc.extract_verse(cuerpo)
        self.assertEqual(texto, "עַל־פְּנֵ֣י׃")
        self.assertEqual(marca, "")

    def test_seg_anidado_dentro_de_w(self):
        # Tehilim 80:14: letra suspendida dentro de la palabra
        cuerpo = '<w lemma="m/3293 a">מִ/יָּ֑<seg type="x-suspended">עַ</seg>ר</w>'
        texto, _ = wlc.extract_verse(cuerpo)
        self.assertEqual(texto, "מִיָּ֑עַר")

    def test_marca_de_parrafo_aparte(self):
        cuerpo = '<w>x</w><seg type="x-sof-pasuq">׃</seg><seg type="x-pe">פ</seg>'
        texto, marca = wlc.extract_verse(cuerpo)
        self.assertEqual(texto, "x׃")
        self.assertEqual(marca, "פ")

    def test_nota_descartada(self):
        texto, _ = wlc.extract_verse('<note n="c">aparato crítico</note><w>שָׁל֑וֹם</w>')
        self.assertEqual(texto, "שָׁל֑וֹם")

    def test_paseq_es_palabra_propia(self):
        texto, _ = wlc.extract_verse('<w>א</w><seg type="x-paseq">׀</seg><w>ב</w>')
        self.assertEqual(texto, "א ׀ ב")

    def test_salida_en_nfc(self):
        texto, _ = wlc.extract_verse('<w>שָׁמַ֖ע</w>')
        self.assertEqual(texto, unicodedata.normalize("NFC", texto))

    def test_strip_marks(self):
        self.assertEqual(wlc.strip_marks("בְּרֵאשִׁ֖ית בָּרָ֣א"), "בראשית ברא")


class TestCatalogo(unittest.TestCase):
    def test_39_libros_y_secciones(self):
        self.assertEqual(len(slugs.BOOKS), 39)
        cuenta = {}
        for b in slugs.BOOKS:
            cuenta[b["section"]] = cuenta.get(b["section"], 0) + 1
        self.assertEqual(cuenta, {"torah": 5, "neviim": 21, "ketuvim": 13})

    def test_orden_continuo(self):
        self.assertEqual(sorted(b["order"] for b in slugs.BOOKS), list(range(1, 40)))

    def test_resolve_alias(self):
        for entrada, esperado in [("genesis", "bereshit"), ("GÉNESIS", "bereshit"),
                                  ("exodo", "shemot"), ("salmos", "tehilim"),
                                  ("1 Samuel", "shmuel_a"), ("bereshit", "bereshit")]:
            self.assertEqual(slugs.resolve(entrada), esperado, entrada)
        self.assertIsNone(slugs.resolve("libro-inexistente"))


class TestReglaCurada(unittest.TestCase):
    def test_yoel_y_malaquias_cuadran(self):
        esperado = {"yoel": {1: 20, 2: 27, 3: 5, 4: 21},
                    "malakhi": {1: 14, 2: 17, 3: 24}}
        with open(VALERA, encoding="utf-8") as fh:
            chaps = json.load(fh)["books"]
        for slug, caps in esperado.items():
            for cap, n in caps.items():
                es_chaps = {}
                for libro in chaps:
                    if libro["name"] == slugs.BY_SLUG[slug]["rv1909"]:
                        es_chaps = {int(c["chapter"]): [{"n": int(v["verse"]), "es": v["text"]}
                                                        for v in c["verses"]] for c in libro["chapters"]}
                filas = curated.slice_es(es_chaps, slug, cap)
                self.assertIsNotNone(filas, "%s/%d" % (slug, cap))
                self.assertEqual(len(filas), n, "%s/%d" % (slug, cap))
                self.assertTrue(all(f[2] for f in filas), "todas con cita es_ref")


@unittest.skipUnless(os.path.isdir(WLC_DIR), "faltan las fuentes: corre build/fetch_sources.sh")
class TestBuild(unittest.TestCase):
    def test_un_libro(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(wlc=WLC_DIR, valera=VALERA, out=tmp, lang="he",
                                      book="bereshit", books=False, no_check=False)
            build_data.build(args)
            caps = sorted(os.listdir(os.path.join(tmp, "he", "bereshit")))
            self.assertEqual(len(caps), 50)
            d = json.load(open(os.path.join(tmp, "he", "bereshit", "1.json")))
            self.assertEqual(d["counts"]["verses"], 31)
            self.assertEqual(d["verses"][0]["he_plain"], "בראשית ברא אלהים את השמים ואת הארץ")
            self.assertFalse(os.path.exists(os.path.join(tmp, "index.json")))

    def test_alineacion_es(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(wlc=WLC_DIR, valera=VALERA, out=tmp, lang="es",
                                      book="yoel", books=False, no_check=False)
            build_data.build(args)
            d = json.load(open(os.path.join(tmp, "es", "yoel", "3.json")))
            self.assertEqual(d["alignment"]["he"], 5)
            self.assertTrue(d["alignment"]["curated"])
            self.assertEqual(d["verses"][0]["es_ref"], "2:28")


if __name__ == "__main__":
    unittest.main(verbosity=2)
