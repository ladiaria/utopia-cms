from __future__ import unicode_literals

from django.urls import re_path

from .views import TopicListView, TopicDetailView, question_detail


urlpatterns = [
    re_path(r'^$', TopicListView.as_view(), name='faq-topic-list'),
    re_path(r'^(?P<slug>[-\w]+)/$', TopicDetailView.as_view(), name='faq-topic-detail'),
    re_path(r'^(?P<topic_slug>[-\w]+)/(?P<slug>[-\w]+)/$', question_detail, name='faq-question-detail'),
]
