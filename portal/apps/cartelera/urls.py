from django.urls import path, re_path
from cartelera.views import index, categoria, cine, pelicula, obrateatro, evento, notification, notification_closed


urlpatterns = [
    path('', index, name='cartelera',),
    re_path(r'^cine/(?P<slug>[-\w]+)/$', cine, name='cine',),
    re_path(r'^cine/pelicula/(?P<slug>[-\w]+)/$', pelicula, name='pelicula',),
    re_path(r'^teatro/obra/(?P<slug>[-\w]+)/$', obrateatro, name='teatro',),
    re_path(r'^evento/(?P<slug>[-\w]+)/$', evento, name='evento',),
    path('live_embed_event/notification/', notification, name='live-embed-event-notification'),
    path(
        'live_embed_event/<int:live_embed_event_id>/closed/',
        notification_closed,
        name='live-embed-event-notification-closed',
    ),
    re_path(r'^(?P<slug>[-\w]+)/$', categoria, name='categoria_evento'),
]
