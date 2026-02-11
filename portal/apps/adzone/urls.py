from django.urls import path, re_path

from .views import ad_view, ad_content


urlpatterns = [
    re_path(r'^view/(?P<id>[\d]+)/(?P<tracking>.*)$', ad_view, name='adzone_ad_view'),
    path('content/', ad_content, name='adzone_ad_content'),
]
