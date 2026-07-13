/**
 * {{ site.name }} service worker.
 *
 * @version {{ version }}
 *
 */

var staticCacheNamePrefix = "{{ site.name }}-v";
var staticCacheName = staticCacheNamePrefix + "{{ version }}";
var filesToCache = [{% block files_to_cache %}
  '/static/meta/utopia-1024x1024.png',
  '/static/meta/utopia-512x512.png',
  '/static/meta/utopia-192x192.png'{% endblock %}
];
// Caches left behind by service workers of previous installations, deleted on activate.
var legacyCacheNames = [{% block legacy_cache_names %}{% endblock %}];

self.addEventListener('install', function(e) {
  self.skipWaiting();
  e.waitUntil(
    caches.open(staticCacheName).then(function(cache) {
      return cache.addAll(filesToCache);
    })
  );
});

// The handler must exist even though it does nothing: Chrome only fires
// `beforeinstallprompt` — which the add-to-home-screen banner depends on — when the
// service worker registers a fetch handler. Nothing is cached at runtime, so it never
// calls respondWith() and every request reaches the network untouched.
self.addEventListener('fetch', e => {
  {% block fetch_body %}{% endblock %}
});

self.addEventListener('activate', e => {
  e.waitUntil(clients.claim());
  e.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        // deletes any legacy cache plus every staticCache other than the current one
        cacheNames.filter(function(cacheName) {
          return legacyCacheNames.indexOf(cacheName) !== -1 || (
            cacheName.startsWith(staticCacheNamePrefix) && cacheName != staticCacheName
          );
        }).map(function(cacheName) {
          return caches.delete(cacheName);
        })
      );
    })
  );
});

{% if push_notifications_keys_set %}
  self.addEventListener('push', function(e) {
    if (e.data) {
      var options = e.data.json();
    } else {
      body = '{{ site.name }}.';
    }

    e.waitUntil(
      self.registration.showNotification('{{ site.name }}', options)
    );
  });

  self.addEventListener('notificationclick', e => {
    const notification = e.notification;
    const link = notification.data.link;
    const action = e.action;

    if (action === 'close') {
      notification.close();
    } else {
      clients.openWindow(link);
      notification.close();
    }
  });
{% endif %}
