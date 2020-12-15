from django.conf.urls import patterns, url
from cartelera.views import index, categoria, cine, pelicula, rating, obrateatro, evento, notification_closed

urlpatterns = patterns(
    '',
    url(r'^$', index, name='cartelera'),
    url(r'^cine/(?P<slug>[-\w]+)/$', cine, name='cine'),
    url(r'^cine/pelicula/(?P<slug>[-\w]+)/$', pelicula, name='pelicula'),
    url(r'^teatro/obra/(?P<slug>[-\w]+)/$', obrateatro, name='teatro'),
    url(r'^evento/(?P<slug>[-\w]+)/$', evento, name='evento'),
    url(r'^live_embed_event/(?P<live_embed_event_id>\d+)/closed/$',
        notification_closed, name='live-embed-event-notification-closed'),
    url(r'^rating/$', rating, name='rating'),
    url(r'^(?P<slug>[-\w]+)/$', categoria, name='categoria_evento'),
)
