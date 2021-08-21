from django.conf.urls import url

from adzone.views import ad_view, ad_content

urlpatterns = [
    url(r'^view/(?P<id>[\d]+)/(?P<tracking>.*)$', ad_view,
        name='adzone_ad_view'),
    url(r'^content/$', ad_content, name='adzone_ad_content'),
]
