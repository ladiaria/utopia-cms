from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView

from faq.models import Topic, Question


class TopicListView(ListView):
    """
    A list view of all published FAQ topics.

    Templates:
        :template:`faq/topic_list.html`
    Context:
        topic_list
            A list of all published :model:`faq.Topic` objects that
            relate to the current :model:`sites.Site`.

    """

    model = Topic
    context_object_name = 'topic'


class TopicDetailView(DetailView):
    """
    A detail view of an FAQ topic.

    Templates:
        ``<topic_template_name>``
            If the :model:`faq.Topic` object has a ``template_name`` value,
            the system will attempt to load that template.
        :template:`faq/topic_detail.html`
            If there is no ``template_name`` given or the template specified
            does not exist the standard template will be used.
    Context:
        topic
            An :model:`faq.Topic` object.
    """
    model = Topic
    context_object_name = 'topic'
    queryset = Topic.published.all()


def question_detail(request, topic_slug, slug):
    """
    A detail view of a Question.

    This view simply redirects to a detail page for the :model:`faq.Question`
    object's related :model:`faq.Topic`, with the addition of a fragment
    identifier that links to the given :model:`faq.Question`, e.g.
    ``faq/topic-slug/#question-slug``.

    Note that a 404 will be raised if the :model:`faq.Question` is not
    published (i.e. it is drafted or removed).

    Thus, the templates and context are those used on the
    :view:`faq.views.topic_detail` view.

    """
    get_object_or_404(Question.published.filter(slug=slug, topic__slug=topic_slug))
    topic_url = reverse('faq-topic-detail', kwargs={'slug': topic_slug})
    question_fragment = '#%s' % slug

    return redirect(topic_url + question_fragment, permanent=True)
