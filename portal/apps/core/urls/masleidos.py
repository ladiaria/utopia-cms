from django.conf.urls.defaults import patterns, url

from core.views.masleidos import index, content

urlpatterns = patterns(
    '',
    url(r'^$', index, name='mas_leidos'),
    url(r'^content/$', content, name='mas_leidos_content'),
)
