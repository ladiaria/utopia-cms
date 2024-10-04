from django.urls import path, re_path
from django.views.generic import TemplateView

from updown.views import AddRatingFromModel
from .views import (
    add_article,
    edit_article,
    add_registro,
    article_detail,
    add_evento,
    edit_evento,
    beneficios,
    index,
    profile,
    VerifyQRView,
    SendQRByEmailView,
)


urlpatterns = [
    path('', index, name='comunidad'),
    path('perfil/', profile, name='comunidad_profile'),
    re_path(r'^article/(?P<slug>[-\w]+)$', article_detail, name='comunidad_article_detail'),
    path('add/article', add_article, name='comunidad_article_add'),
    re_path(r'^edit/article/(?P<slug>[-\w]+)$', edit_article, name='comunidad_article_edit'),
    re_path(r'^evento/(?P<slug>[-\w]+)$', article_detail, name='comunidad_evento_detail'),
    re_path(r'^add/evento', add_evento, name='comunidad_evento_add'),
    re_path(r'^edit/evento/(?P<slug>[-\w]+)$', edit_evento, name='comunidad_evento_edit'),
    re_path(
        r"^(?P<object_id>\d+)/rate/(?P<score>[\d\-]+)$",
        AddRatingFromModel(),
        {'app_label': 'comunidad', 'model': 'SubscriberArticle', 'field_name': 'rating'},
        name="article_rating",
    ),
    re_path(r'^formaparte', TemplateView.as_view(template_name='comunidad/formaparte.html'), name='formaparte'),
    re_path(r'beneficios', beneficios, name='beneficios'),
    re_path(r'^registro/(?P<beneficio_id>\d+)/(?P<hashed_subscriber_id>[\w]+)/$', add_registro),
    path('verify-registro/<str:hashed_id>/', VerifyQRView.as_view(), name='verify_registro'),
    path('send-qr-by-email/<str:registro_id>/', SendQRByEmailView.as_view(), name='send_qr_by_email'),
]
