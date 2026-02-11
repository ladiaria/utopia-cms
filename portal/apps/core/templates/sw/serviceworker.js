/**
 * {{ site.name }} service worker.
 *
 * @version {{ version }}
 *
 */

var staticCacheNamePrefix = "{{ site.name }}-v";
var staticCacheName = staticCacheNamePrefix + new Date().getTime();
var filesToCache = [{% block files_to_cache %}
  '/static/meta/utopia-1024x1024.png',
  '/static/meta/utopia-512x512.png',
  '/static/meta/utopia-192x192.png'{% endblock %}
];

self.addEventListener('install', function(e) {
  self.skipWaiting();
  e.waitUntil(
    caches.open(staticCacheName).then(function(cache) {
      return cache.addAll(filesToCache);
    })
  );
});

self.addEventListener('fetch', e => {
  {% block fetch_begin %}{% endblock %}
  {% block fetch_body %}
    e.respondWith(
      caches.match(e.request).then(response => {

        if (response) {
          return response;
        } else {

          return (async () => {
            try {
              // Try to fetch the request from the network
              const response = await fetch(e.request);
              if (!response || response.status !== 200 || response.type !== 'basic') {
                return response; // Return the original response if valid
              }
              // optionally cache, disabled (TODO: investigate)
              // const responseClone = response.clone();
              // caches.open(staticCacheName).then(cache => cache.put(e.request, responseClone));
              return response;
            } catch (error) {
              console.warn('SW fetch failed:', error);
              // Optionally return a fallback response, e.g., an offline page
              return caches.match('/offline.html') || new Response('Network error occurred', {
                status: 503,
                statusText: 'Service Unavailable',
              });
            }
          })();

        }
      })
    );
  {% endblock %}
});

self.addEventListener('activate', e => {
  e.waitUntil(clients.claim());
  e.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        // deletes the previous staticCache (TODO: confirm this assumption)
        cacheNames.filter(function(cacheName) {
          return cacheName.startsWith(staticCacheNamePrefix) && cacheName != staticCacheName;
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
