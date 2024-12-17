from django.urls import re_path

from core.views.publication import NewsletterPreview


urlpatterns = [
    re_path(r'^(?P<publication_slug>\w+)/$', NewsletterPreview.as_view(), name='publication-nl-preview'),
]
