from __future__ import unicode_literals
from django.conf.urls import *

from faq.views import TopicListView, TopicDetailView, question_detail


urlpatterns = [

    url(r'^$', TopicListView.as_view(), name='faq-topic-list'),
    url(r'^(?P<slug>[-\w]+)/$', TopicDetailView.as_view(),
        name='faq-topic-detail'),
    url(r'^(?P<topic_slug>[-\w]+)/(?P<slug>[-\w]+)/$', question_detail,
        name='faq-question-detail'),
]
