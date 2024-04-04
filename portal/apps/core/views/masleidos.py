from __future__ import unicode_literals

from django.conf import settings
from django.db.models.aggregates import Sum
from django.views.decorators.cache import never_cache
from django.utils.timezone import now, timedelta

from decorators import render_response

from core.models import Article, ArticleViews


to_response = render_response('core/templates/')


def mas_leidos(days=1, cover=False, limit=10):
    """
    Returns the top (upto limit) most viewed articles counting days days ago from now.
    If cover is True, articles in satirical sections are excluded. (Issue4910).
    Rare but possible: exclude articles with an empty slug because they will raise exception when computing their urls.
    """
    desde, more_exclude_kwargs = now().date() - timedelta(days), {}
    if cover:
        more_exclude_kwargs['article__sections__slug__in'] = getattr(settings, 'CORE_SATIRICAL_SECTIONS', ())
    return [
        Article.objects.get(id=av['article']) for av in ArticleViews.objects.filter(
            article__is_published=True, day__gt=desde
        ).exclude(
            article__slug=''
        ).exclude(
            **more_exclude_kwargs
        ).values('article').annotate(total_views=Sum('views')).order_by('-total_views')[:limit]
    ]


def mas_leidos_daily(cover=False, limit=None):
    days_ago = 1 if now().date().isoweekday() < 7 else 2
    return mas_leidos(days_ago, cover, limit) if limit else mas_leidos(days_ago, cover)


@never_cache
@to_response
def index(request):
    return (
        'masleidos_view.html',
        {
            'mas_leidos_daily': mas_leidos_daily(),
            'mas_leidos_weekly': mas_leidos(7),
            'mas_leidos_monthly': mas_leidos(30),
        },
    )


@to_response
def content(request):
    return 'masleidos.html', {'masleidos_cover_daily': mas_leidos_daily(True, 5)}
