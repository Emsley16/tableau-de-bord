// Service worker — stratégie « réseau d'abord »
// L'application se met à jour à chaque ouverture connectée.
// Le cache ne sert que de secours hors connexion : il ne retarde jamais une mise à jour.

const CACHE = "bilan-secours";

self.addEventListener("install", () => {
  // La nouvelle version prend la main sans attendre la fermeture des onglets
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const cles = await caches.keys();
    await Promise.all(cles.filter(k => k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  // Les appels externes (Base Adresse Nationale, relais d'analyse) passent directement
  if (url.origin !== location.origin) return;

  event.respondWith((async () => {
    try {
      const frais = await fetch(req, { cache: "no-store" });
      if (frais && frais.status === 200) {
        const c = await caches.open(CACHE);
        c.put(req, frais.clone());
      }
      return frais;
    } catch (e) {
      const garde = await caches.match(req);
      if (garde) return garde;
      if (req.mode === "navigate") {
        const index = await caches.match("./index.html") || await caches.match("./");
        if (index) return index;
      }
      throw e;
    }
  })());
});
