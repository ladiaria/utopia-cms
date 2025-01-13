from pydoc import locate

from django.conf import settings
from django.urls import re_path

from ..views import publication


pub_preview_classname = getattr(settings, 'CORE_PUBLICATIONS_NL_PREVIEW_CLASSNAME', None)
NewsletterPreviewClass = locate(pub_preview_classname) if pub_preview_classname else publication.NewsletterPreview

urlpatterns = [
    re_path(r'^(?P<publication_slug>[\w-]+)/$', NewsletterPreviewClass.as_view(), name='publication-nl-preview'),
    re_path(
        r'^(?P<slug>[\w-]+)/browser-preview/$', publication.nl_browser_authpreview, name='p-nl-browser-authpreview'
    ),
    re_path(r'^(?P<publication_slug>[\w-]+)/(?P<hashed_id>\w+)/$', publication.NewsletterBrowserPreview.as_view()),
]
