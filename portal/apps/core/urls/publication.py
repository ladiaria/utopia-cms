from django.urls import re_path

from core.views.publication import NewsletterPreview, NewsletterBrowserPreview, nl_browser_authpreview


urlpatterns = [
    re_path(r'^(?P<publication_slug>[\w-]+)/$', NewsletterPreview.as_view(), name='publication-nl-preview'),
    re_path(r'^(?P<slug>[\w-]+)/browser-preview/$', nl_browser_authpreview, name='p-nl-browser-authpreview'),
    re_path(r'^(?P<publication_slug>[\w-]+)/(?P<hashed_id>\w+)/$', NewsletterBrowserPreview.as_view()),
]
