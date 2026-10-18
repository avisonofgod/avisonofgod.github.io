/* Pruebas del lector (index.html) sin navegador: jsdom + la API real del repo.
 *
 *   NODE_PATH=/ruta/a/node_modules node tests/reader-test.js
 *
 * Verifica navegación, lectura, alineación he/es, búsqueda, toggles, enlaces
 * permanentes y que NO haya recursos externos.
 */
const fs = require("fs");
const path = require("path");

let JSDOM;
try { ({ JSDOM } = require("jsdom")); }
catch (e) { ({ JSDOM } = require("/tmp/jtest/node_modules/jsdom")); }

const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");

let ok = 0, fail = 0;
const chk = (cond, label, detail) => {
  if (cond) { ok++; console.log("OK   " + label + (detail ? " | " + detail : "")); }
  else { fail++; console.log("FALLA " + label + (detail ? " | " + detail : "")); }
};
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
// comparación robusta: sin niqqud/te'amim (el orden de signos no debe romper la prueba)
const letters = (s) => (s || "").replace(/[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]/g, "");

async function boot() {
  const dom = new JSDOM(html, {
    url: "http://localhost/",
    runScripts: "dangerously",
    pretendToBeVisual: true,
    beforeParse(win) {
      win.fetch = async (url) => {
        const p = path.join(ROOT, String(url).replace(/^\//, ""));
        if (!fs.existsSync(p)) return { ok: false, status: 404, json: async () => ({}) };
        return { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(p, "utf8")) };
      };
      win.Element.prototype.scrollIntoView = () => {};
      win.scrollTo = () => {};
      win.__clip = null;
      Object.defineProperty(win.navigator, "clipboard", {
        configurable: true,
        value: { writeText: async (t) => { win.__clip = t; } },
      });
    },
  });
  const { window } = dom;
  await wait(300);
  return window;
}

(async () => {
  const w = await boot();
  const $ = (s) => w.document.querySelector(s);
  const $$ = (s) => Array.from(w.document.querySelectorAll(s));

  // 1) sin recursos externos
  const ext = $$("script[src], link[href]").map((e) => e.getAttribute("src") || e.getAttribute("href"))
    .filter((u) => u && /^https?:/i.test(u));
  chk(ext.length === 0, "sin recursos externos (JS/CSS propios)", ext.join(","));

  // 2) navegación por secciones
  const details = $$("#nav details");
  chk(details.length === 3, "navegación con 3 secciones", details.length);
  chk($$("#nav a[data-book]").length === 39, "39 libros listados", $$("#nav a[data-book]").length);
  const sumaCap = w.Tanaj.state.idx.books.reduce((a, b) => a + b.chapters, 0);
  const sumaVer = w.Tanaj.state.idx.books.reduce((a, b) => a + b.verses, 0);
  chk(sumaCap === 929, "index: 929 capítulos", sumaCap);
  chk(sumaVer === 23213, "index: 23.213 versículos", sumaVer);

  // 3) capítulo por defecto
  chk($("#titulo").textContent === "Génesis 1", "abre en Génesis 1", $("#titulo").textContent);
  let rows = $$("#verses li");
  chk(rows.length === 31, "Génesis 1 trae 31 versículos", rows.length);
  chk(letters(rows[0].querySelector(".he").textContent).includes("בראשית ברא אלהים"), "primer versículo con hebreo");
  chk(/En el principio creó אלהים/i.test(rows[0].querySelector(".es").textContent), "y su español (RV1909 + enmienda)");
  chk((rows[0].querySelector(".es small.ver") || {}).textContent === "v1.0",
      "versículo marcado con la versión", (rows[0].querySelector(".es small.ver") || {}).textContent);
  chk(/7 en v1\.0/.test($("#meta").textContent), "meta cuenta los versículos de la versión", $("#meta").textContent);

  // 4) enlace permanente a un versículo
  w.location.hash = "#/tehilim/23/1";
  await wait(400);
  chk($("#titulo").textContent === "Salmos 23", "deep link a Salmos 23", $("#titulo").textContent);
  chk($$("#verses li.hit").length === 1, "versículo resaltado por el enlace", $$("#verses li.hit").length);

  // 5) alias en la URL (genesis -> bereshit)
  w.location.hash = "#/genesis/2";
  await wait(400);
  chk(w.Tanaj.state.slug === "bereshit" && w.Tanaj.state.chapter === 2, "alias 'genesis' → bereshit", w.location.hash);
  chk($("#titulo").textContent === "Génesis 2", "título correcto tras el alias", $("#titulo").textContent);

  // 6) Shemá (Devarim 6:4) en hebreo y español
  w.location.hash = "#/devarim/6";
  await wait(400);
  const v4 = $$("#verses li")[3];
  chk(letters(v4.querySelector(".he").textContent).startsWith("שמע ישראל"), "Devarim 6:4 en hebreo (Shemá)", letters(v4.querySelector(".he").textContent).slice(0, 22));
  chk(/Oye, Israel/i.test(v4.querySelector(".es").textContent), "Devarim 6:4 en español", v4.querySelector(".es").textContent.slice(0, 32));

  // 7) botones de idioma y niqqud
  $$(".seg button").find((b) => b.dataset.mode === "he").click();
  chk(w.document.body.classList.contains("mode-he"), "modo solo hebreo");
  $$(".seg button").find((b) => b.dataset.mode === "both").click();
  $("#nk").click();
  await wait(400);
  chk(!/[\u0591-\u05bd]/.test($$("#verses li")[3].querySelector(".he").textContent), "toggle niqqud: muestra he_plain");
  $("#nk").click();
  await wait(300);

  // 8) navegación de capítulo
  const antes = $("#titulo").textContent;
  $("#next").click();
  await wait(400);
  chk($("#titulo").textContent === "Deuteronomio 7", "siguiente capítulo", antes + " → " + $("#titulo").textContent);

  // 9) el enlace "Ver JSON" apunta a la API
  chk(/\/v1\/he\/devarim\/7\.json$/.test($("#api").getAttribute("href")), "enlace al JSON del capítulo", $("#api").getAttribute("href"));

  // 10) numeración distinta: Bamidbar 16 (35 he / 50 es)
  w.location.hash = "#/bamidbar/16";
  await wait(500);
  const n16 = $$("#verses li");
  chk($("#aviso").textContent.includes("Numeración distinta"), "aviso de numeración distinta");
  chk(n16.length === 50, "se muestran hebreo(35)+español sueltos(15)", n16.length);

  // 11) libros curados: Yoel 3 con es_ref 2:28
  w.location.hash = "#/yoel/3";
  await wait(500);
  const yo = $$("#verses li");
  chk(yo.length === 5, "Yoel 3 trae 5 versículos", yo.length);
  chk(yo[0].querySelector(".es").textContent.includes("(2:28)"), "cita original RV1909 (2:28)",
      yo[0].querySelector(".es").textContent.slice(-8));

  // 12) búsqueda en el Tanaj (hebreo sin niqqud y español con acentos)
  w.Tanaj.state.allSections = true;
  const box = $("#q");
  box.value = "שמע ישראל";
  box.dispatchEvent(new w.Event("input", { bubbles: true }));
  await wait(1200);
  const hits = $$("#results .hit");
  chk(hits.length > 0, "búsqueda hebrea 'שמע ישראל' devuelve resultados", hits.length);
  chk(hits.some((h) => /Deuteronomio 6:4/.test(h.textContent)), "y encuentra Devarim 6:4");
  box.value = "derramare mi espiritu";
  box.dispatchEvent(new w.Event("input", { bubbles: true }));
  await wait(1200);
  chk($$("#results .hit").some((h) => /Joel 3:1/.test(h.textContent)),
      "búsqueda española sin acentos → Joel 3:1 (derramaré mi Espíritu)");

  // 12) marcador de la versión propia עבדיהו: componentes hebreos <-> palabras españolas
  box.value = "";
  box.dispatchEvent(new w.Event("input", { bubbles: true }));
  w.location.hash = "#/bereshit/1";
  await wait(500);
  const li1 = $$("#verses li")[0];
  const heComp = Array.from(li1.querySelectorAll(".he .w"));
  const esPal = Array.from(li1.querySelectorAll(".es .w"));
  chk(heComp.length === 11, "Gen 1:1: 7 palabras partidas en 11 componentes", heComp.length);
  chk(esPal.length === 10, "y 10 tokens españoles", esPal.length);
  const bet = heComp.find((c) => c.textContent === "בְּ");
  const resh = heComp.find((c) => c.textContent === "רֵאשִׁ֖ית");
  chk(!!bet && bet.dataset.s === "P/b#0", "el prefijo בְּ trae su id", bet && bet.dataset.s);
  chk(!!resh && resh.dataset.s === "H7225#0", "la raíz רֵאשִׁית trae su Strong",
      resh && resh.dataset.s);
  const marcados = (sel) => Array.from(li1.querySelectorAll(sel)).map((e) => e.textContent).join(" ");

  // cursor (sin nada fijo) -> se marca el par completo
  resh.dispatchEvent(new w.Event("mouseover", { bubbles: true }));
  chk(marcados(".es .w.marca") === "principio", "cursor en רֵאשִׁית marca «principio»",
      marcados(".es .w.marca"));
  resh.dispatchEvent(new w.Event("mouseout", { bubbles: true }));
  chk(li1.querySelectorAll(".w.marca").length === 0, "al salir el cursor se limpia");

  // clic en el prefijo -> solo «En»; clic en la raíz -> solo «principio»
  bet.dispatchEvent(new w.Event("click", { bubbles: true }));
  chk(marcados(".es .w.marca") === "En", "clic en בְּ marca solo «En»", marcados(".es .w.marca"));
  resh.dispatchEvent(new w.Event("click", { bubbles: true }));
  chk(marcados(".es .w.marca") === "principio", "clic en רֵאשִׁית marca «principio»",
      marcados(".es .w.marca"));
  chk(marcados(".he .w.marca") === "רֵאשִׁ֖ית", "y queda marcada la raíz elegida",
      marcados(".he .w.marca"));
  chk(/H7225/.test($("#marca-info").textContent), "el pie muestra el Strong",
      $("#marca-info").textContent.trim().slice(0, 40));

  // español -> hebreo, y cada artículo con SU id (no todos los de la clase)
  const los = esPal.find((e) => e.textContent === "los");
  los.dispatchEvent(new w.Event("click", { bubbles: true }));
  chk(marcados(".he .w.marca") === "הַ", "clic en «los» marca el artículo הַ",
      marcados(".he .w.marca"));
  chk(marcados(".es .w.marca") === "los", "solo ese artículo, no «la»", marcados(".es .w.marca"));
  const la = esPal.find((e) => e.textContent === "la");
  la.dispatchEvent(new w.Event("click", { bubbles: true }));
  chk(marcados(".es .w.marca") === "la" && marcados(".he .w.marca") === "הָ",
      "clic en «la» marca el otro artículo (הָ)", marcados(".es .w.marca") + " / " + marcados(".he .w.marca"));

  // partícula sin pareja: no marca nada
  const elArt = esPal.find((e) => e.textContent === "el");
  elArt.dispatchEvent(new w.Event("click", { bubbles: true }));
  chk(li1.querySelectorAll(".w.marca").length === 0,
      "«el» no se une a ningún componente: no marca", String(elArt.dataset.s));

  // versículo ajeno a la versión propia (1:8): sin componentes ni marcador
  const liAjeno = $$("#verses li")[7];
  chk(liAjeno.querySelectorAll(".he .w").length === 0 && liAjeno.querySelectorAll(".es .w").length === 0,
      "versículo sin versión propia: sin componentes",
      liAjeno.querySelectorAll(".w").length);

  // 13) desglose por letra de la palabra seleccionada (panel dentro del nav)
  chk(!!$("#letras") && !!$("#nav").querySelector("section.letras"),
      "el nav trae el panel de letras",
      $("#letras") && $("#letras").querySelector("h2").textContent);
  resh.dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(80);
  const filas = Array.from($("#letras").querySelectorAll("li"));
  chk(filas.length === 5, "רֵאשִׁית se descompone en 5 letras", filas.length);
  chk(filas.map((f) => f.querySelector(".heb").textContent).join("") === "ראשית",
      "letras en orden: Resh, Aleph, Shin, Yod, Tav",
      filas.map((f) => f.querySelector("b").textContent).join(" "));
  chk(/Resh/.test(filas[0].textContent) && /El primero, el l\u00edder, la persona principal/.test(filas[0].textContent),
      "Resh -> «El primero, el líder, la persona principal»", filas[0].textContent.trim());
  bet.dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(80);
  const filaBet = $("#letras").querySelector("li");
  chk(!!filaBet && /Bet/.test(filaBet.textContent) && /Familia, dentro, el hogar/.test(filaBet.textContent),
      "בְּ -> Bet -> «Familia, dentro, el hogar»", filaBet && filaBet.textContent.trim());
  const laEs = esPal.find((e) => e.textContent === "la");
  laEs.dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(80);
  chk($("#letras").querySelectorAll("li").length === 1,
      "desde el español se desglosa su componente hebreo (הָ -> He)",
      $("#letras").textContent.replace(/\s+/g, " ").slice(0, 70));
  chk($("#letras").querySelector("li") === $("#letras").querySelectorAll("li")[0] &&
      /He/.test($("#letras").textContent), "He -> «Ventana, he aquí, revelar, aliento»",
      $("#letras").querySelector("li").textContent.trim());

  // 14) las secciones del nav se pliegan al seleccionar y quedan separadas de «Letras»
  const secs = () => Array.from($("#nav").querySelectorAll("details"));
  chk(!!$("#nav .secciones") && !$("#nav .secciones").contains($("#letras")),
      "secciones separadas del panel de letras");
  chk(secs().length === 3, "3 secciones en el nav", secs().length);
  chk(secs().every((d) => !d.open), "con palabra seleccionada, las secciones están plegadas",
      secs().map((d) => (d.open ? "abierta" : "plegada")).join(","));
  laEs.dispatchEvent(new w.Event("click", { bubbles: true }));       // segundo clic: se quita
  await wait(60);
  chk(secs().some((d) => d.open), "al quitar el marcador se restauran",
      secs().map((d) => (d.open ? "abierta" : "plegada")).join(","));
  chk(/pictográfica/.test($("#letras").textContent), "y el panel vuelve a su ayuda");
  resh.dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(60);
  chk(secs().every((d) => !d.open) && $("#letras").querySelectorAll("li").length === 5,
      "vuelve a plegarse al seleccionar y muestra las letras",
      $("#letras").querySelectorAll("li").length);

  // 15) Gen 1:2: el selector sigue el mapa del autor (palabra hebrea <-> traducción)
  const li2 = $$("#verses li")[1];
  const comp2 = (id) => li2.querySelector(".he .w[data-s='" + id + "']");
  const tok2 = (id) => Array.from(li2.querySelectorAll(".es .w")).find((e) => e.dataset.s === id);
  chk(!!comp2("H776#0") && tok2("H776#0") && tok2("H776#0").textContent === "tierra",
      "אָרֶץ queda con «tierra»", tok2("H776#0") && tok2("H776#0").textContent);
  chk(!!comp2("H1961#1") && tok2("H1961#1").textContent === "era", "הָיְתָה queda con «era»");
  chk(tok2("H8414#2").textContent === "caos" && tok2("H922#3").textContent === "desolación,",
      "תֹּהוּ -> «caos» y בֹּהוּ -> «desolación»");
  chk(tok2("H8415#6").textContent === "abismo," && tok2("H4325#11").textContent === "aguas.",
      "תְּהוֹם -> «abismo» y מַיִם -> «aguas»");
  chk(tok2("H7307#7").textContent === "espíritu" && tok2("H430#8").textContent === "אלהים",
      "רוּחַ -> «espíritu» y אֱלֹהִים -> «אלהים» (sin traducir)");
  chk(tok2("P/c#0").textContent === "Y" && tok2("P/d#0").textContent === "la",
      "וְ -> «Y» y הָ -> «la»", tok2("P/c#0").textContent + "/" + tok2("P/d#0").textContent);
  chk(tok2("H5921#5").textContent === "sobre" && tok2("H6440#10").textContent === "superficie",
      "עַל -> «sobre» (1.º) y פְּנֵי -> «superficie» (2.º)");
  chk(tok2("H5921#10").textContent === "sobre" && tok2("H5921#5") !== tok2("H5921#10"),
      "las dos apariciones de עַל quedan separadas");

  const marcados2 = (sel) => Array.from(li2.querySelectorAll(sel)).map((e) => e.textContent).join(" ");
  const marcados3 = (sel) => Array.from(li3v.querySelectorAll(sel)).map((e) => e.textContent).join(" ");
  comp2("H776#0").dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(60);
  chk(marcados2(".es .w.marca") === "tierra", "clic en אָרֶץ marca solo «tierra»",
      marcados2(".es .w.marca"));
  chk(marcados2(".he .w.marca") === "אָ֗רֶץ", "y el componente hebreo", marcados2(".he .w.marca"));
  chk(/H776/.test($("#marca-info").textContent), "el pie indica el Strong", $("#marca-info").textContent.trim());
  const parts = Array.from(li2.querySelectorAll(".es .w"));
  const suelta = parts[parts.findIndex((e) => e.textContent === "las")];
  suelta.dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(40);
  chk(li2.querySelectorAll(".w.marca").length === 0,
      "«las» de «y las tinieblas» no se une a nadie: no marca", JSON.stringify(suelta.dataset.s));

  // 16) Bereshit 1:3: «Y dijo Dios: exista la luz y existió la luz.»
  const li3v = $$("#verses li")[2];
  const esTexto3 = li3v.querySelector(".es").textContent.replace(/\s+v1\.0\s*$/, "").trim();
  chk(esTexto3 === "Y dijo אלהים, exista luz y existió luz.",
      "texto final de 1:3", esTexto3);
  const t3 = (id) => Array.from(li3v.querySelectorAll(".es .w")).find((e) => e.dataset.s === id);
  chk(t3("H559#0").textContent === "dijo" && t3("H430#1").textContent === "אלהים,",
      "וַיֹּאמֶר -> «dijo» y אֱלֹהִים -> «אלהים» (sin traducir)");
  chk(Array.from(li3v.querySelectorAll(".es .w")).filter((e) => !e.dataset.s).length === 0,
      "1:3 sin palabras sueltas: todas tienen pareja");
  chk(t3("H1961#2").textContent === "exista" && t3("H1961#4").textContent === "existió",
      "יְהִי -> «exista» y וַיְהִי -> «existió» (cada aparición aparte)");
  chk(t3("H216#3").textContent === "luz" && t3("H216#4").textContent === "luz.",
      "אוֹר -> «luz» en sus dos apariciones");
  li3v.querySelector(".he .w[data-s='H1961#2']").dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(50);
  chk(marcados3(".es .w.marca") === "exista", "clic en יְהִי marca solo «exista»",
      marcados3(".es .w.marca"));
  li3v.querySelector(".he .w[data-s='H1961#4']").dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(50);
  chk(marcados3(".es .w.marca") === "existió", "clic en וַיְהִי marca solo «existió»",
      marcados3(".es .w.marca"));

  // 17) Bereshit 1:4: אֶת y el 2.º בֵּין también en hebreo/directos
  const li4 = $$("#verses li")[3];
  const T4 = "Y vio אלהים la luz buena, y separó אלהים entre la luz y entre las tinieblas.";
  const esTexto4 = li4.querySelector(".es").textContent.replace(/\s+v1\.0\s*$/, "").trim();
  chk(esTexto4 === T4, "texto final de 1:4", esTexto4);
  const t4 = (id) => Array.from(li4.querySelectorAll(".es .w")).find((e) => e.dataset.s === id);
  chk(t4("H853#2") === undefined && !li4.querySelector(".es").textContent.includes("את"),
      "אֶת no se muestra en la traducción");
  chk(t4("H2896#3").textContent === "buena," && t4("H3588#3") === undefined,
      "כִּי no se traduce: solo טוֹב -> «buena»");
  chk(t4("H996#6").textContent === "entre" && t4("H996#8").textContent === "entre",
      "los dos בֵּין con id propio (H996#6 / H996#8)");
  chk(t4("H7200#0").textContent === "vio" && t4("H914#4").textContent === "separó",
      "וַיַּרְא -> «vio» y וַיַּבְדֵּל -> «separó»");
  chk(li4.querySelectorAll(".es .w").length === 16 &&
      Array.from(li4.querySelectorAll(".es .w")).every((e) => e.dataset.s),
      "1:4 sin palabras sueltas: 16 de 16 con pareja");
  // el marcador alef-tav lleva su nota al panel de letras
  li4.querySelector(".he .w[data-s='H853#2']").dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(60);
  chk(/Alef-tav/.test($("#letras").textContent) &&
      /acción directa del verbo/.test($("#letras").textContent),
      "nota de alef-tav en el panel de letras", $("#letras").textContent.slice(-90));
  chk(Array.from($("#letras").querySelectorAll("li .heb")).map((e) => e.textContent).join("") === "את",
      "y las dos letras: Alef y Tav");
  li4.querySelector(".he .w[data-s='H2822#9']").dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(50);
  const marca4 = () => Array.from(li4.querySelectorAll(".es .w.marca"))
    .map((e) => e.textContent).join(" ");
  chk(marca4() === "tinieblas.", "clic en חֹשֶׁךְ marca «tinieblas.»", marca4());
  li4.querySelector(".he .w[data-s='P/d#9']").dispatchEvent(new w.Event("click", { bubbles: true }));
  await wait(50);
  chk(marca4() === "las", "clic en el artículo הַ marca «las»", marca4());

  // 18) Bereshit 1:5: nombres puestos a la luz y a las tinieblas
  const li5 = $$("#verses li")[4];
  const T5 = "Y llamó אלהים la luz día, y las tinieblas llamó noche, y fue anochecer y fue " +
    "amanecer, día primero.";
  const esTexto5 = li5.querySelector(".es").textContent.replace(/\s+v1\.0\s*$/, "").trim();
  chk(esTexto5 === T5, "texto final de 1:5", esTexto5);
  const t5 = (id) => Array.from(li5.querySelectorAll(".es .w")).find((e) => e.dataset.s === id);
  chk(t5("H3117#4").textContent === "día," && t5("H3915#7").textContent === "noche,",
      "יוֹם -> «día» y לַיְלָה -> «noche»");
  chk(t5("H6153#8").textContent === "anochecer" && t5("H1242#9").textContent === "amanecer,",
      "עֶרֶב -> «anochecer» y בֹּקֶר -> «amanecer»");
  chk(t5("H259#11").textContent === "primero.", "אֶחָד -> «primero»");
  chk(t5("H7121#0").textContent === "llamó" && t5("H7121#6").textContent === "llamó",
      "las dos formas de קָרָא con id propio");
  chk(li5.querySelectorAll(".es .w").length === 19 &&
      Array.from(li5.querySelectorAll(".es .w")).every((e) => e.dataset.s),
      "1:5 sin palabras sueltas: 19 de 19 con pareja");
  chk(t5("P/c#8").textContent === "y" && t5("H1961#8").textContent === "fue",
      "la «y» de וַיְהִי queda con su וַ (P/c#8)");

  // 19) Bereshit 1:6: la expansión y el separador entre las aguas
  const li6 = $$("#verses li")[5];
  const T6 = "Y dijo אלהים exista expansión en medio las aguas, y sea separador entre aguas " +
    "de las aguas.";
  const esTexto6 = li6.querySelector(".es").textContent.replace(/\s+v1\.0\s*$/, "").trim();
  chk(esTexto6 === T6, "texto final de 1:6", esTexto6);
  const t6 = (id) => Array.from(li6.querySelectorAll(".es .w")).find((e) => e.dataset.s === id);
  chk(t6("H7549#3").textContent === "expansión" && t6("H914#7").textContent === "separador",
      "רָקִיעַ -> «expansión» y מַבְדִּיל -> «separador»");
  chk(t6("P/b#4").textContent === "en" && t6("H8432#4").textContent === "medio",
      "בְּתוֹךְ -> «en» + «medio»");
  chk(t6("H996#8").textContent === "entre" && t6("P/l#10").textContent === "de",
      "בֵּין -> «entre» y לָ -> «de»");
  chk(li6.querySelectorAll(".es .w").length === 17 &&
      Array.from(li6.querySelectorAll(".es .w")).every((e) => e.dataset.s),
      "1:6 sin palabras sueltas: 17 de 17 con pareja");

  // 20) Bereshit 1:7: separación de las aguas de debajo y de sobre la expansión
  const li7 = $$("#verses li")[6];
  const T7 = "Y hizo אלהים la expansión, y separó entre las aguas que debajo de la expansión " +
    "y entre las aguas que encima de la expansión. Y fue así.";
  const esTexto7 = li7.querySelector(".es").textContent.replace(/\s+v1\.0\s*$/, "").trim();
  chk(esTexto7 === T7, "texto final de 1:7", esTexto7);
  const t7 = (id) => Array.from(li7.querySelectorAll(".es .w")).find((e) => e.dataset.s === id);
  chk(t7("H6213#0").textContent === "hizo" && t7("H914#3").textContent === "separó",
      "וַיַּעַשׂ -> «hizo» y וַיַּבְדֵּל -> «separó»");
  chk(t7("H996#4").textContent === "entre" && t7("H996#9").textContent === "entre",
      "los dos בֵּין con id propio");
  chk(t7("P/m#7") !== t7("P/m#12"), "los dos prefijos מ quedan separados");
  chk(t7("H8478#7").textContent === "debajo" && t7("P/m#7").textContent === "de",
      "מִתַּחַת -> «debajo» + «de» (el prefijo מ va después en español)");
  chk(t7("H5921#12").textContent === "encima" && t7("P/m#12").textContent === "de",
      "מֵעַל -> «encima» + «de»");
  chk(t7("H3651#14").textContent === "así." && t7("H1961#14").textContent === "fue" &&
      t7("P/c#14").textContent === "Y", "וַיְהִי־כֵן -> «Y fue así»");
  chk(li7.querySelectorAll(".es .w").length === 27 &&
      Array.from(li7.querySelectorAll(".es .w")).every((e) => e.dataset.s),
      "1:7 sin palabras sueltas: 27 de 27 con pareja");

  // copiar sigue trayendo el texto completo (los spans no lo rompen)
  li1.querySelector("[data-copy]").dispatchEvent(new w.Event("click", { bubbles: true }));
  chk(/En el principio creó אלהים/.test(w.__clip || ""), "Copiar incluye el español",
      String(w.__clip).split("\n")[2]);

  console.log("\n== RESUMEN: " + ok + " OK / " + fail + " FALLA ==");
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
