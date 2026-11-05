const CACHE = 'rahgard-shell-v3';
const ASSETS = [
  '/', '/manifest.webmanifest', '/mark.svg', '/fonts/estedad.css',
  '/fonts/estedad-arabic-variable.woff2', '/fonts/estedad-latin-variable.woff2',
  ...['naghshe-jahan', 'fin-garden', 'yazd-windcatchers', 'qeshm-hara'].flatMap(name =>
    [640, 960, 1280].flatMap(width => [`/images/${name}-${width}.webp`, `/images/${name}-${width}.avif`])),
];
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS))));
self.addEventListener('activate', event => event.waitUntil(Promise.all([
  self.clients.claim(),
  caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('rahgard-shell-') && key !== CACHE).map(key => caches.delete(key)))),
])));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;

  // Always ask the server for the latest app shell while online. A cache-first
  // navigation can replay a production index.html on a Vite dev server, whose
  // hashed production bundle no longer exists, producing a blank page and 404.
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        void caches.open(CACHE).then(cache => cache.put(event.request, copy));
      }
      return response;
    }).catch(() => caches.match(event.request).then(cached => cached || caches.match('/'))));
    return;
  }

  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    if (response.ok) { const copy = response.clone(); void caches.open(CACHE).then(cache => cache.put(event.request, copy)); }
    return response;
  }).catch(() => Response.error())));
});
