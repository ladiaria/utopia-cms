/**
 * utopia-cms service worker.
 *
 * Service worker to control de PWA feature.
 *
 * @version {{ version }}
 *
 */

var staticCacheName = "utopia-pwa-v" + new Date().getTime();
var filesToCache = [
  '/static/meta/utopia-512x512.png'
];

self.addEventListener('install', function(e) {
  self.skipWaiting();
  e.waitUntil(
    caches.open(staticCacheName).then(function(cache) {
      return cache.addAll([
        filesToCache
      ]);
    })
  );
});

self.addEventListener('fetch', function(e) {
  // TODO: we can create a "runtime" cache to store the fetched response (django-progressive-webapp does this)
  e.respondWith(
    caches.match(e.request).then(function(response) {
      return response || fetch(e.request);
    })
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(clients.claim());
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        // deletes the previous staticCache (TODO: confirm this assumption)
        cacheNames.filter(function(cacheName) {
          return cacheName.startsWith('utopia-pwa-') && cacheName != staticCacheName;
        }).map(function(cacheName) {
          return caches.delete(cacheName);
        })
      );
    })
  );
});
