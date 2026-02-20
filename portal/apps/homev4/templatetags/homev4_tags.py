import datetime

from django import template
from django.db.models import Sum
from django.template import loader
from django.utils import timezone
from django.utils.safestring import mark_safe

from core.models import Article, ArticleViews, Section, Category, get_current_edition


register = template.Library()

SLOT_TEMPLATES = {
    "inicio": "homev4/slot_renderers/inicio.html",
    "componentes": "homev4/slot_renderers/componentes.html",
    "area": "homev4/slot_renderers/area.html",
    "most_read": "homev4/slot_renderers/most_read.html",
    "latest": "homev4/slot_renderers/latest.html",
}


@register.simple_tag(takes_context=True)
def render_slot(context, slot_data):
    """Render a single slot from the grid_data JSON based on its content_type."""
    content_type = slot_data.get("content_type", "")
    template_name = SLOT_TEMPLATES.get(content_type)
    if not template_name:
        return mark_safe(f'<div class="slot-error">Unknown content type: {content_type}</div>')

    slot_context = context.flatten()
    slot_context["slot"] = slot_data

    if content_type == "inicio":
        article_ids = slot_data.get("article_ids")
        if article_ids:
            articles_by_id = {a.id: a for a in Article.published.filter(id__in=article_ids)}
            slot_context["top_articles"] = [
                articles_by_id[aid] for aid in article_ids if aid in articles_by_id
            ]
        else:
            edition = get_current_edition()
            slot_context["top_articles"] = list(edition.top_articles)[:7] if edition else []

    elif content_type == "area":
        area_type = slot_data.get("area_type")
        area_id = slot_data.get("area_id")
        slot_context["area_name"] = slot_data.get("area_name", "")
        slot_context["articles"] = []
        if area_type == "section" and area_id:
            try:
                section = Section.objects.get(pk=area_id)
                slot_context["area_name"] = section.name
                slot_context["area_url"] = section.get_absolute_url()
                slot_context["articles"] = list(section.latest(limit=2))
            except Section.DoesNotExist:
                pass
        elif area_type == "category" and area_id:
            try:
                category = Category.objects.get(pk=area_id)
                slot_context["area_name"] = category.name
                slot_context["area_url"] = f"/{category.slug}/"
                if hasattr(category, "home"):
                    slot_context["articles"] = list(category.home.articles_ordered()[:2])
            except Category.DoesNotExist:
                pass

    elif content_type == "most_read":
        try:
            week_ago = timezone.now().date() - datetime.timedelta(days=7)
            most_read_ids = list(
                ArticleViews.objects.filter(day__gte=week_ago)
                .values("article_id")
                .annotate(total=Sum("views"))
                .order_by("-total")
                .values_list("article_id", flat=True)[:10]
            )
            slot_context["most_read_articles"] = list(Article.published.filter(id__in=most_read_ids))
        except Exception:
            slot_context["most_read_articles"] = list(Article.published.order_by("-date_published")[:10])

    elif content_type == "latest":
        limit = slot_data.get("article_limit", 5)
        slot_context["latest_articles"] = Article.published.order_by("-date_published")[:limit]

    return loader.render_to_string(template_name, slot_context)
