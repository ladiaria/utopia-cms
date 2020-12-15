from django.conf.urls.defaults import *

urlpatterns = patterns('tagging_autocomplete_tagit.views',
    url(r'^list$', 'list_tags', name='tagging_autocomplete_tagit-list'),
)
