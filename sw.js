/* Service worker del lector del Tanaj: textos guardados para leer sin conexión.
   Estrategia: `v1/` cache-primero (los datos no cambian sin un nuevo build),
   el resto red-primero con respaldo en caché. */
const CACHE = "tanaj-v1.4";
const CORE = ["./", "index.html", "api.html", "manifest.webmanifest", "v1/index.json",
              "v1/align.json", "v1/versions.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) =>
    Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  if (url.pathname.includes("/v1/")) {                       // datos: caché primero
    e.respondWith(caches.open(CACHE).then((c) =>
      c.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res.ok) c.put(req, res.clone());
        return res;
      }))));
    return;
  }
  e.respondWith(fetch(req).then((res) => {
    if (res.ok && (req.mode === "navigate" || /\.(html|css|js|svg|webmanifest)$/.test(url.pathname))) {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy));
    }
    return res;
  }).catch(() => caches.match(req).then((hit) => hit || caches.match("index.html"))));
});
