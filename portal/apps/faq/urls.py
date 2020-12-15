from django.conf.urls.defaults import *

from faq.views import TopicListView, TopicDetailView, question_detail


urlpatterns = patterns(
    '',
    url(r'^$', TopicListView.as_view(), name='faq-topic-list'),
    url(r'^(?P<slug>[-\w]+)/$', TopicDetailView.as_view(),
        name='faq-topic-detail'),
    url(r'^(?P<topic_slug>[-\w]+)/(?P<slug>[-\w]+)/$', question_detail,
        name='faq-question-detail'),
)
