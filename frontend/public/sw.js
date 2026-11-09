const CACHE = 'rahgard-shell-v4';
const ASSETS = [
  '/', '/manifest.webmanifest', '/mark.svg', '/icons/icon-192.png', '/icons/icon-512.png', '/fonts/estedad.css',
  '/fonts/estedad-arabic-variable.woff2', '/fonts/estedad-latin-variable.woff2',
  ...['naghshe-jahan', 'fin-garden', 'yazd-windcatchers', 'qeshm-hara'].flatMap(name =>
    [640, 960, 1280].flatMap(width => [`/images/${name}-${width}.webp`, `/images/${name}-${width}.avif`])),
];
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS))));
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});
self.addEventListener('activate', event => event.waitUntil(Promise.all([
  self.clients.claim(),
  caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('rahgard-shell-') && key !== CACHE).map(key => caches.delete(key)))),
])));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;
  // The production catalogue is dynamic. Never cache empty, stale, or user-visible
  // API responses in the shared PWA shell cache.
  if (new URL(event.request.url).pathname.startsWith('/api/')) return;

  // Always ask the server for the latest app shell while online. A cache-first
  // navigation can replay a production index.html on a Vite dev server, whose
  // hashed production bundle no longer exists, producing a blank page and 404.
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/')));
    return;
  }

  // Only explicitly listed, public shell assets may enter or be read from cache.
  // Other same-origin resources can carry user-specific content.
  if (!ASSETS.includes(new URL(event.request.url).pathname)) return;
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
