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
      win.navigator.clipboard = { writeText: async () => {} };
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
  chk(/EN el principio/i.test(rows[0].querySelector(".es").textContent), "y su español (RV1909)");

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

  console.log("\n== RESUMEN: " + ok + " OK / " + fail + " FALLA ==");
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
