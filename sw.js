const CACHE = 'taxi-murcia-shell-v1';
const SHELL = [
  './',
  './index.html',
  './leaflet.css',
  './leaflet.js',
  './supabase.min.js',
  './manifest.webmanifest',
  './icon-192.svg',
  './icon-512.svg'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

// HTML is network-first so a new published version is picked up quickly.
// Local static assets use the cache as a fallback when the connection drops.
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const request = event.request;
  const isNavigation = request.mode === 'navigate' || request.url.endsWith('/index.html');
  event.respondWith(
    isNavigation
      ? fetch(request, { cache: 'no-store' }).then(response => {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put('./index.html', copy));
          return response;
        }).catch(() => caches.match('./index.html'))
      : caches.match(request).then(cached => cached || fetch(request).then(response => {
          if (new URL(request.url).origin === self.location.origin) {
            const copy = response.clone();
            caches.open(CACHE).then(cache => cache.put(request, copy));
          }
          return response;
        }))
  );
});

// The server will send these payloads when push notifications are enabled.
self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (_) {
    data = { title: 'Taxi Murcia', body: event.data ? event.data.text() : 'Hay una actualización' };
  }
  const title = data.title || 'Taxi Murcia';
  const options = {
    body: data.body || 'Hay un nuevo servicio disponible.',
    icon: './icon-192.svg',
    badge: './icon-192.svg',
    tag: data.tag || 'taxi-murcia-service',
    renotify: true,
    vibrate: [250, 100, 250],
    data: { url: data.url || './' },
    actions: [{ action: 'open', title: 'Abrir servicio' }]
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target = event.notification.data && event.notification.data.url || './';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      const sameOrigin = list.find(client => client.url.startsWith(self.location.origin));
      if (sameOrigin) return sameOrigin.focus();
      return clients.openWindow(target);
    })
  );
});
