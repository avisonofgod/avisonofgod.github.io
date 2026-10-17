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
  chk(/En el principio creó Elohim/i.test(rows[0].querySelector(".es").textContent), "y su español (RV1909 + enmienda)");
  chk((rows[0].querySelector(".es small.ver") || {}).textContent === "v1.0",
      "versículo marcado con la versión", (rows[0].querySelector(".es small.ver") || {}).textContent);
  chk(/2 en v1\.0/.test($("#meta").textContent), "meta cuenta los versículos de la versión", $("#meta").textContent);

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
  chk(!!resh && resh.dataset.s === "H7225", "la raíz רֵאשִׁית trae su Strong",
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

  // versículo ajeno a la versión propia: sin componentes ni marcador
  const li3 = $$("#verses li")[2];
  chk(li3.querySelectorAll(".he .w").length === 0 && li3.querySelectorAll(".es .w").length === 0,
      "versículo sin versión propia: sin componentes",
      li3.querySelectorAll(".w").length);

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
  chk(!!comp2("H776") && tok2("H776") && tok2("H776").textContent === "tierra",
      "אָרֶץ queda con «tierra»", tok2("H776") && tok2("H776").textContent);
  chk(!!comp2("H1961") && tok2("H1961").textContent === "era", "הָיְתָה queda con «era»");
  chk(tok2("H8414").textContent === "caos" && tok2("H922").textContent === "desolación,",
      "תֹהוּ -> «caos» y בֹהוּ -> «desolación»");
  chk(tok2("H8415").textContent === "abismo," && tok2("H4325").textContent === "aguas.",
      "תְּהוֹם -> «abismo» y מַיִם -> «aguas»");
  chk(tok2("H7307").textContent === "espíritu" && tok2("H430").textContent === "Dios",
      "רוּחַ -> «espíritu» y אֱלֹהִים -> «Dios»");
  chk(tok2("P/c#0").textContent === "Y" && tok2("P/d#0").textContent === "la",
      "וְ -> «Y» y הָ -> «la»", tok2("P/c#0").textContent + "/" + tok2("P/d#0").textContent);
  chk(tok2("H5921") && tok2("H5921").textContent === "sobre" && tok2("H6440").textContent === "superficie",
      "עַל -> «sobre» y פְּנֵי -> «superficie»");

  const marcados2 = (sel) => Array.from(li2.querySelectorAll(sel)).map((e) => e.textContent).join(" ");
  comp2("H776").dispatchEvent(new w.Event("click", { bubbles: true }));
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

  // copiar sigue trayendo el texto completo (los spans no lo rompen)
  li1.querySelector("[data-copy]").dispatchEvent(new w.Event("click", { bubbles: true }));
  chk(/En el principio creó Elohim/.test(w.__clip || ""), "Copiar incluye el español",
      String(w.__clip).split("\n")[2]);

  console.log("\n== RESUMEN: " + ok + " OK / " + fail + " FALLA ==");
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
