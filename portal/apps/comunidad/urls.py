from __future__ import absolute_import
from __future__ import unicode_literals
from django.conf.urls import url
from django.views.generic import TemplateView

from updown.views import AddRatingFromModel
from .views import (
    add_article, edit_article, add_registro, article_detail, add_evento, edit_evento, beneficios, index, profile
)


urlpatterns = [
    url(r'^$', index, name='comunidad', ),
    url(r'^perfil/$', profile, name='comunidad_profile'),
    url(r'^article/(?P<slug>[-\w]+)$', article_detail, name='comunidad_article_detail'),
    url(r'^add/article$', add_article, name='comunidad_article_add'),
    url(r'^edit/article/(?P<slug>[-\w]+)$', edit_article, name='comunidad_article_edit'),
    url(r'^evento/(?P<slug>[-\w]+)$', article_detail, name='comunidad_evento_detail'),
    url(r'^add/evento', add_evento, name='comunidad_evento_add'),
    url(r'^edit/evento/(?P<slug>[-\w]+)$', edit_evento, name='comunidad_evento_edit'),
    url(
        r"^(?P<object_id>\d+)/rate/(?P<score>[\d\-]+)$",
        AddRatingFromModel(),
        {'app_label': 'comunidad', 'model': 'SubscriberArticle', 'field_name': 'rating'},
        name="article_rating",
    ),
    url(r'^formaparte', TemplateView.as_view(template_name='comunidad/formaparte.html'), name='formaparte'),
    url(r'beneficios', beneficios, name='beneficios'),
    url(r'^registro/(?P<beneficio_id>\d+)/(?P<hashed_subscriber_id>[\w]+)/$', add_registro)
]
