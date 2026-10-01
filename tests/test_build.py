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
import es_verses                                     # noqa: E402
import import_es_version as imp_es                   # noqa: E402
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


class TestVersionesES(unittest.TestCase):
    """Capas de versión española (build/es_versions/) sobre la RV1909."""

    def test_capa_katznelson_declarada(self):
        capas = es_verses.load()
        nombres = [c["version"] for c in capas]
        self.assertIn("Moisés Katznelson", nombres)
        capa = [c for c in capas if c["version"] == "Moisés Katznelson"][0]
        self.assertEqual(capa["verses"][("bereshit", 1, 1)],
                         "En el principio creó Elohim los cielos y la tierra.")
        self.assertTrue(capa["license"], "la capa declara su licencia")
        self.assertTrue(capa["file"].endswith(".json"))

    def test_apply_marca_es_version(self):
        chaps = {1: [{"n": 1, "es": "EN el principio crió Dios los cielos y la tierra."},
                     {"n": 2, "es": "Y la tierra estaba desordenada y vacía."},
                     {"n": 3, "es": "Y dijo Dios: Sea la luz."}]}
        self.assertEqual(es_verses.apply(chaps, "bereshit"), 2)
        self.assertEqual(chaps[1][0]["es_version"], "Katznelson")
        self.assertEqual(chaps[1][1]["es_version"], "Katznelson")
        self.assertNotIn("es_version", chaps[1][2])
        primera = chaps[1][1]["es"]
        es_verses.apply(chaps, "bereshit")          # idempotente
        self.assertEqual(chaps[1][1]["es"], primera)
        otro = {1: [{"n": 1, "es": "x"}]}
        self.assertEqual(es_verses.apply(otro, "shemot"), 0)
        self.assertEqual(otro[1][0]["es"], "x")

    def test_payload_declara_y_aplica(self):
        capas = es_verses.load()
        payload = {c["version"]: c for c in es_verses.payload({"Moisés Katznelson": 2}, capas)}
        k = payload["Moisés Katznelson"]
        self.assertEqual(k["verses_declared"], 2)
        self.assertEqual(k["verses_applied"], 2)
        self.assertTrue(k["file"].startswith("build/es_versions/"))
        self.assertEqual(payload["Moisés Katznelson"]["short"], "Katznelson")

    def test_carga_ignora_json_ajenos(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "otro.json"), "w", encoding="utf-8") as fh:
                fh.write('{"foo": 1}')
            with open(os.path.join(tmp, "roto.json"), "w", encoding="utf-8") as fh:
                fh.write("{no es json")
            with open(os.path.join(tmp, "capa.json"), "w", encoding="utf-8") as fh:
                json.dump({"version": "Prueba", "short": "Prueba",
                           "books": {"bereshit": {"1": {"1": "texto"}},
                                     "libro_inventado": {"1": {"1": "x"}}}}, fh)
            capas = es_verses.load(tmp)
            self.assertEqual([c["version"] for c in capas], ["Prueba"], "solo la capa válida")
            self.assertEqual(capas[0]["verses"], {("bereshit", 1, 1): "texto"},
                             "el libro desconocido se descarta")

    def test_importador_parsea_referencias(self):
        versos, malas = imp_es.parsear_versos(
            "Génesis 1:1\tEn el principio creó Elohim\n"
            "Bereshit 1:2 Pero la tierra\n   desierta y vacía\n"
            "basura sin referencia\n")
        self.assertEqual(versos[("bereshit", 1, 1)], "En el principio creó Elohim")
        self.assertEqual(versos[("bereshit", 1, 2)],
                         "Pero la tierra desierta y vacía basura sin referencia",
                         "las líneas sin referencia se acumulan al versículo anterior")
        self.assertEqual(malas, [], "ninguna línea se descarta")
        self.assertEqual(imp_es.parsear_versos("Salmos 23:1 YHVH es mi pastor")[0],
                         {("tehilim", 23, 1): "YHVH es mi pastor"})
        self.assertEqual(imp_es._por_rv1909("Génesis"), "bereshit")
        self.assertIsNone(imp_es._por_rv1909("Libro Inventado"))
        self.assertIn("Kapítulo", imp_es.parsear_versos("Kapítulo 1:1 texto")[1][0])

    @unittest.skipUnless(os.path.isdir(WLC_DIR), "faltan las fuentes: corre build/fetch_sources.sh")
    def test_build_es_marca_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(wlc=WLC_DIR, valera=VALERA, out=tmp, lang="es",
                                      book="bereshit", books=False, no_check=False)
            build_data.build(args)
            d = json.load(open(os.path.join(tmp, "es", "bereshit", "1.json")))
            self.assertEqual(d["verses"][0]["es_version"], "Katznelson")
            self.assertEqual(d["verses"][1]["es_version"], "Katznelson")
            self.assertNotIn("es_version", d["verses"][2])
            self.assertEqual(d["verses"][2]["es"], "Y dijo Dios: Sea la luz: y fué la luz.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
