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

{% if push_notifications_keys_set %}
  self.addEventListener('push', function(e) {
    if (e.data) {
      const splited_message = e.data.text().split('|');
      body = splited_message[0];
      tag = splited_message[1];
      link = splited_message[2];
    } else {
      body = '{{ site.name }}.';
    }

    var options = {
      body: body,
      tag: tag,
      icon: '/static/meta/utopia-192x192.png',
      vibrate: [100, 50, 100],
      data: {
        link: link
      },
      actions: [
        {action: 'explore', title: 'Ir al sitio web', icon: '/static/meta/utopia-192x192.png'},
        {action: 'close', title: 'Close', icon: '/static/meta/utopia-192x192.png'}
      ]
    };
    e.waitUntil(
      self.registration.showNotification('{{ site.name }}', options)
    );
  });

  self.addEventListener('notificationclick', event => {
    const notification = event.notification;
    const link = notification.data.link;
    const action = event.action;

    if (action === 'close') {
      notification.close();
    } else {
      clients.openWindow(link);
      notification.close();
    }
  });
{% endif %}
