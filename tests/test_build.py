"""Pruebas del generador del Tanaj (sin red). Ejecutar: python3 -m unittest discover -s tests -v"""

# pyright: reportMissingImports=false  (los módulos de build/ se añaden al sys.path abajo)

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unicodedata
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "build"))

import build_data                                    # noqa: E402
import curated                                       # noqa: E402
import es_verses
import letras
import strong_es                                     # noqa: E402
import import_es_version as imp_es                   # noqa: E402
import slugs                                         # noqa: E402
import wlc                                           # noqa: E402

WLC_DIR = os.path.join(RAIZ, "data", "morphhb", "wlc")
OUT_DIR = os.path.join(RAIZ, "v1")
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
                                      book="bereshit", books=False, no_check=False,
                                      strong=build_data.STRONG_LAYER, no_strong=True)
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
                                      book="yoel", books=False, no_check=False,
                                      strong=build_data.STRONG_LAYER, no_strong=True)
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
        self.assertIn("1.0", nombres)
        capa = [c for c in capas if c["version"] == "1.0"][0]
        self.assertEqual(capa["verses"][("bereshit", 1, 1)],
                         "En el principio creó אלהים los cielos y la tierra.")
        self.assertEqual(capa["author"], "עבדיהו")
        self.assertTrue(capa["spdx"], "la capa declara licencia SPDX")
        self.assertIn("CC0", capa["license"])
        self.assertTrue(capa["file"].endswith(".json"))

    def test_apply_marca_es_version(self):
        chaps = {1: [{"n": 1, "es": "EN el principio crió Dios los cielos y la tierra."},
                     {"n": 2, "es": "Y la tierra estaba desordenada y vacía."},
                     {"n": 3, "es": "Y dijo Dios: Sea la luz."},
                     {"n": 4, "es": "Y vio Dios que la luz era buena."}]}
        self.assertEqual(es_verses.apply(chaps, "bereshit"), 3)
        self.assertEqual(chaps[1][0]["es_version"], "v1.0")
        self.assertEqual(chaps[1][1]["es_version"], "v1.0")
        self.assertEqual(chaps[1][2]["es"], "Y dijo אלהים, exista luz y existió luz.")
        self.assertNotIn("es_version", chaps[1][3])
        primera = chaps[1][1]["es"]
        es_verses.apply(chaps, "bereshit")          # idempotente
        self.assertEqual(chaps[1][1]["es"], primera)
        otro = {1: [{"n": 1, "es": "x"}]}
        self.assertEqual(es_verses.apply(otro, "shemot"), 0)
        self.assertEqual(otro[1][0]["es"], "x")

    def test_payload_declara_y_aplica(self):
        capas = es_verses.load()
        payload = {c["version"]: c for c in es_verses.payload({"1.0": 3}, capas)}
        k = payload["1.0"]
        self.assertEqual(k["verses_declared"], 3)
        self.assertEqual(k["verses_applied"], 3)
        self.assertTrue(k["file"].startswith("build/es_versions/"))
        self.assertEqual(k["short"], "v1.0")
        self.assertEqual(k["author"], "עבדיהו")
        self.assertEqual(k["spdx"], "CC0-1.0")

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
            "Génesis 1:1\tEn el principio creó אלהים\n"
            "Bereshit 1:2 Pero la tierra\n   desierta y vacía\n"
            "basura sin referencia\n")
        self.assertEqual(versos[("bereshit", 1, 1)], "En el principio creó אלהים")
        self.assertEqual(versos[("bereshit", 1, 2)],
                         "Pero la tierra desierta y vacía basura sin referencia",
                         "las líneas sin referencia se acumulan al versículo anterior")
        self.assertEqual(malas, [], "ninguna línea se descarta")
        self.assertEqual(imp_es.parsear_versos("Salmos 23:1 YHVH es mi pastor")[0],
                         {("tehilim", 23, 1): "YHVH es mi pastor"})
        self.assertEqual(imp_es._por_rv1909("Génesis"), "bereshit")
        self.assertIsNone(imp_es._por_rv1909("Libro Inventado"))
        self.assertIn("Kapítulo", imp_es.parsear_versos("Kapítulo 1:1 texto")[1][0])

    def test_importador_filtra_y_no_deja_huecos(self):
        """La capa escrita no debe incluir versículos que no existen en el hebreo."""
        with tempfile.TemporaryDirectory() as tmp:
            entrada = os.path.join(tmp, "in.tsv")
            with open(entrada, "w", encoding="utf-8") as fh:
                fh.write("Génesis 1:1\ttexto válido\nGénesis 99:9\tfuera del Tanaj\n")
            salida = os.path.join(tmp, "capa.json")
            r = subprocess.run([sys.executable, os.path.join(RAIZ, "build", "import_es_version.py"),
                                "--in", entrada, "--out", salida, "--version", "Prueba",
                                "--license", "x", "--out-json", os.path.join(RAIZ, "v1")],
                               capture_output=True, text=True, cwd=RAIZ)
            capa = json.load(open(salida, encoding="utf-8"))
            self.assertEqual(capa["books"], {"bereshit": {"1": {"1": "texto válido"}}})
            self.assertNotEqual(r.returncode, 0, "avisa de la referencia sin hebreo")
            self.assertIn("sin hebreo", r.stdout)
            self.assertIn("99:9", r.stdout)

    @unittest.skipUnless(os.path.isdir(WLC_DIR), "faltan las fuentes: corre build/fetch_sources.sh")
    def test_build_es_marca_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(wlc=WLC_DIR, valera=VALERA, out=tmp, lang="es",
                                      book="bereshit", books=False, no_check=False,
                                      strong=build_data.STRONG_LAYER, no_strong=False)
            build_data.build(args)
            d = json.load(open(os.path.join(tmp, "es", "bereshit", "1.json")))
            self.assertEqual(d["verses"][0]["es_version"], "v1.0")
            self.assertEqual(d["verses"][1]["es_version"], "v1.0")
            self.assertEqual(d["verses"][2]["es_version"], "v1.0")
            self.assertEqual(d["verses"][2]["es"], "Y dijo אלהים, exista luz y existió luz.")
            self.assertNotIn("es_version", d["verses"][3], "el resto sigue siendo RV1909")


class TestLetrasHebreas(unittest.TestCase):
    """Abecedario con lectura pictográfica: build/letras.py -> v1/letras.json."""

    def test_tabla_de_letras(self):
        p = os.path.join(os.path.dirname(build_data.__file__), "letras.py")
        self.assertTrue(os.path.isfile(p), "fuente única en build/letras.py")
        d = letras.payload()
        self.assertEqual(len(d["letters"]), 22)
        self.assertEqual(len(d["order"]), 22)
        for letra, v in d["letters"].items():
            self.assertIn(letra, d["order"])
            self.assertTrue(v["nombre"] and v["pictograma"], letra)
        self.assertEqual(d["finals"], {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})
        self.assertEqual(d["letters"]["ב"]["nombre"], "Bet")
        self.assertEqual(d["letters"]["ב"]["pictograma"], "Familia, dentro, el hogar")
        self.assertEqual(d["letters"]["ר"]["pictograma"],
                         "El primero, el líder, la persona principal")

    def test_publicado_en_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(wlc=WLC_DIR, valera=VALERA, out=tmp, lang="all",
                                      book="bereshit", books=False, no_check=True,
                                      strong=build_data.STRONG_LAYER, no_strong=False)
            build_data.build(args)
            d = json.load(open(os.path.join(tmp, "letras.json"), encoding="utf-8"))
            self.assertEqual(len(d["letters"]), 22)
            self.assertEqual(d["letters"]["ר"]["nombre"], "Resh")
            idx = json.load(open(os.path.join(OUT_DIR, "index.json"), encoding="utf-8"))
            self.assertIn("letras", idx["sources"], "fuente declarada en /v1/index.json")


class TestStrongDelEspanol(unittest.TestCase):
    """Relación palabra hebrea <-> traducción: SOLO la versión propia v1.0 עבדיהו."""

    @classmethod
    def setUpClass(cls):
        cls.capa = json.load(open(build_data.STRONG_LAYER, encoding="utf-8"))
        cls.capas = es_verses.load()

    def test_declaracion_de_la_capa(self):
        c = self.capa
        self.assertEqual(c["version"], "1.0")
        self.assertEqual(c["author"], "עבדיהו", "sin alias: el autor es עבדיהו")
        self.assertEqual(c["spdx"], "CC0-1.0")
        self.assertIn("morphhb", c["source"])
        self.assertIn("es_versions", c["scope"])

    def test_alcance_solo_la_version_propia(self):
        propias = set()
        for capa in self.capas:
            propias.update((s, c, n) for s, c, n in capa["verses"])
        huerfanos = []
        for slug, caps in self.capa["books"].items():
            for cap, versos in caps.items():
                for n in versos:
                    if (slug, int(cap), int(n)) not in propias:
                        huerfanos.append("%s/%s:%s" % (slug, cap, n))
        self.assertEqual(huerfanos, [], "no se globaliza a versículos ajenos")
        self.assertGreater(len(propias), 0)

    def test_componentes_de_bereshit_1_1(self):
        b = self.capa["books"]["bereshit"]["1"]["1"]
        self.assertEqual(b["hw"][0], "בְּרֵאשִׁ֖ית")
        self.assertEqual(b["hx"][0], [["בְּ", "P/b#0"], ["רֵאשִׁ֖ית", "H7225#0"]],
                         "prefijo y raíz separados, con id por aparición")
        self.assertEqual(b["hs"][0], "H7225", "hs es la raíz")
        es = "En el principio creó אלהים los cielos y la tierra.".split()
        parejas = {t: s for t, s in zip(es, b["st"]) if s}
        self.assertEqual(parejas, {"En": "P/b#0", "principio": "H7225#0", "creó": "H1254#1",
                                   "אלהים": "H430#2", "los": "P/d#4", "cielos": "H8064#4",
                                   "la": "P/d#6", "tierra.": "H776#6"},
                         "«el» y «y» no se unen a nadie")

    def test_particulas_declaradas(self):
        for pid in ("c", "d", "i", "b", "l", "k", "m", "s"):
            self.assertIn(pid, self.capa["prefijos"])
            self.assertIn("clase", self.capa["prefijos"][pid])

    def test_mapa_del_autor_en_bereshit_1_2(self):
        b = self.capa["books"]["bereshit"]["1"]["2"]
        texto = ("Y la tierra era caos y desolación, y las tinieblas sobre el abismo, "
                 "y el espíritu de אלהים aleteaba sobre la superficie de las aguas.")
        parejas = {(t, s) for t, s in zip(texto.split(), b["st"]) if s}
        self.assertEqual(parejas, {
            ("Y", "P/c#0"), ("la", "P/d#0"), ("tierra", "H776#0"), ("era", "H1961#1"),
            ("caos", "H8414#2"), ("y", "P/c#3"), ("desolación,", "H922#3"), ("y", "P/c#4"),
            ("tinieblas", "H2822#4"), ("sobre", "H5921#5"), ("abismo,", "H8415#6"),
            ("y", "P/c#7"), ("espíritu", "H7307#7"), ("אלהים", "H430#8"), ("aleteaba", "H7363#9"),
            ("sobre", "H5921#10"), ("superficie", "H6440#10"), ("las", "P/d#11"),
            ("aguas.", "H4325#11"),
        }, "una aparición de la raíz no marca la otra (H5921#5 vs H5921#10)")
        self.assertEqual(len(b["st"]), len(texto.split()), "un id por token")
        # «el», «de», «las» de «y las tinieblas» y la faz que no aparece: sin pareja
        for token in ("el", "de"):
            self.assertIsNone(b["st"][texto.split().index(token)], token)
        self.assertIsNone(b["st"][8], "«las» de «y las tinieblas» no se une a nadie")

    def test_mapa_del_autor_en_bereshit_1_3(self):
        b = self.capa["books"]["bereshit"]["1"]["3"]
        texto = "Y dijo אלהים, exista luz y existió luz."
        parejas = {(t, s) for t, s in zip(texto.split(), b["st"]) if s}
        self.assertEqual(parejas, {
            ("Y", "P/c#0"), ("dijo", "H559#0"), ("אלהים,", "H430#1"), ("exista", "H1961#2"),
            ("luz", "H216#3"), ("y", "P/c#4"), ("existió", "H1961#4"), ("luz.", "H216#4"),
        })
        self.assertEqual(len(parejas), len(texto.split()), "sin palabras sueltas: todo casa")
        self.assertEqual(b["hw"][0], "וַיֹּ֥אמֶר")
        self.assertEqual(b["hx"][4], [["וַֽ", "P/c#4"], ["יְהִי־", "H1961#4"], ["אֽוֹר׃", "H216#4"]],
                         "el maqqef deja tres componentes en la última palabra")

    def test_glosas_incoherentes_no_se_aplican(self):
        analisis = [("אָ֗רֶץ", "H776", [("אָ֗רֶץ", "H776")])]
        # glosas = [por palabra [por componente [tokens…]]]
        self.assertIsNone(strong_es.etiquetar_por_glosas(analisis, ["tierra"], [[["no-existe"]]]),
                          "token que no está en el texto -> no se aplica")
        self.assertIsNone(strong_es.etiquetar_por_glosas(analisis, ["tierra"], []),
                          "faltan palabras -> no se aplica")
        self.assertIsNone(strong_es.etiquetar_por_glosas(analisis, ["tierra"], [[["tierra"], ["x"]]]),
                          "componentes de más -> no se aplica")
        et, colocados = strong_es.etiquetar_por_glosas(analisis, ["la", "tierra"], [[["tierra"]]])
        self.assertEqual((et, colocados), ([None, "H776"], 1), "«la» queda suelta")

    def test_build_publica_solo_donde_hay_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(wlc=WLC_DIR, valera=VALERA, out=tmp, lang="all",
                                      book="bereshit", books=False, no_check=False,
                                      strong=build_data.STRONG_LAYER, no_strong=False)
            build_data.build(args)
            d = json.load(open(os.path.join(tmp, "he", "bereshit", "1.json")))
            v = d["verses"][0]
            self.assertEqual(" ".join(v["hw"]), v["he"])
            self.assertEqual(len(v["hw"]), len(v["hs"]))
            self.assertEqual(len(v["hw"]), len(v["hx"]))
            for palabra, comps in zip(v["hw"], v["hx"]):
                self.assertEqual("".join(c[0] for c in comps), palabra)
                for _txt, cid in comps:
                    if cid and cid.startswith("P/"):
                        self.assertIn(cid[2], self.capa["prefijos"], "código de prefijo documentado")
            self.assertNotIn("hw", d["verses"][3], "versículo sin versión propia: sin etiquetas")
            e = json.load(open(os.path.join(tmp, "es", "bereshit", "1.json")))
            self.assertEqual(e["verses"][0]["st"],
                             self.capa["books"]["bereshit"]["1"]["1"]["st"])
            self.assertNotIn("st", e["verses"][3], "versículo ajeno: sin etiquetas")


if __name__ == "__main__":
    unittest.main(verbosity=2)
