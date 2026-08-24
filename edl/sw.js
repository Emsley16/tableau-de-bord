/* Relevé — service worker.
   Deux rôles seulement :
   1. rendre l'application utilisable sans réseau, dans un logement vide où le
      mobile n'a souvent qu'une barre ;
   2. détecter une nouvelle version à chaque lancement, sans jamais l'appliquer
      au milieu d'un relevé en cours — c'est l'application qui décide du moment.
   Aucune donnée d'état des lieux ne transite ici : relevés, photos et
   signatures restent dans IndexedDB, sur l'appareil. */

const VERSION = "1.3.0";
const CACHE = "releve-" + VERSION;
const FICHIERS = [
  "./", "./index.html", "./manifest.webmanifest",
  "./icon-180.png", "./icon-192.png", "./icon-512.png", "./icon-512-maskable.png"
];

self.addEventListener("install", e => {
  // Pas de skipWaiting ici : la nouvelle version patiente jusqu'à ce que
  // l'utilisateur accepte la mise à jour depuis l'application.
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FICHIERS)).catch(() => {}));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(noms => Promise.all(noms.filter(n => n !== CACHE).map(n => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", e => {
  if (e.data && e.data.type === "APPLIQUER_MAJ") self.skipWaiting();
  if (e.data && e.data.type === "VERSION") e.source.postMessage({ type: "VERSION", version: VERSION });
});

self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  if (new URL(e.request.url).origin !== location.origin) return;
  // Réseau d'abord : c'est ce qui permet de voir arriver une nouvelle version.
  e.respondWith(
    fetch(e.request)
      .then(rep => {
        const copie = rep.clone();
        caches.open(CACHE).then(c => c.put(e.request, copie)).catch(() => {});
        return rep;
      })
      .catch(() => caches.match(e.request).then(r => r || caches.match("./index.html")))
  );
});
