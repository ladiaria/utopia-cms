from django.template import Template, Library, Context

from thedaily.models import RemainingContent


register = Library()


@register.simple_tag(takes_context=True)
def remaining_articles_content(context=Context({}), optional_value=None):
    # optional value is useful when you do not have a context with a request to use for calling this function
    request = context.get("request")
    remaining_articles = getattr(request, "credits", None) if request else optional_value
    if remaining_articles is not None:
        try:
            content = RemainingContent.objects.get(remaining_articles=remaining_articles).template_content
        except RemainingContent.DoesNotExist:
            content = '<p><a href="{% url "subscribe_landing" %}">Suscribite</a></p>'
        return Template(content).render(context)
    return ""
