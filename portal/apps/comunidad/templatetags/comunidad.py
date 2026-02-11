from django.template import Library

from ..models import SubscriberArticle


register = Library()


@register.inclusion_tag('comunidad/top_comunidad.html', takes_context=True)
def top_comunidad(context):
    return {'articles': SubscriberArticle.top_articles()}
