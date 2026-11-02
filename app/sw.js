/* Service worker ACTU : garde seulement la « coquille » de l'application (≈ 100 Ko) pour démarrer vite.
   Les articles ne sont jamais stockés : ils viennent toujours d'internet. */
const CACHE = 'actu-shell-v1';
const SHELL = ['./', 'index.html', 'app.css', 'app.js', 'themes.json', 'manifest.webmanifest', 'icons/apple-touch-icon.png', 'icons/favicon-32.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Réseau d'abord (toujours la dernière version), cache seulement si hors connexion.
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin || url.pathname.includes('/data/')) return;
  e.respondWith(
    fetch(e.request).then((res) => {
      if (res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
      }
      return res;
    }).catch(() => caches.match(e.request).then((r) => r || caches.match('index.html')))
  );
});
