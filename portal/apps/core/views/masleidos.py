from __future__ import unicode_literals

from datetime import date, timedelta

from django.conf import settings
from django.db.models.aggregates import Sum
from django.views.decorators.cache import never_cache

from decorators import render_response

from core.models import Article, ArticleViews


to_response = render_response('core/templates/')


def mas_leidos(days=1, cover=False):
    """
    Returns the top 10 most viewed articles counting days days ago from now.
    If cover is True, articles in satirical sections are excluded. (Issue4910).
    Rare but possible: exclude articles with an empty slug because they will raise exception when computing their urls.
    """
    desde, more_exclude_kwargs = date.today() - timedelta(days), {}
    if cover:
        more_exclude_kwargs['article__sections__slug__in'] = getattr(settings, 'CORE_SATIRICAL_SECTIONS', ())
    return [
        Article.objects.get(id=av['article']) for av in ArticleViews.objects.filter(
            article__is_published=True, day__gt=desde
        ).exclude(
            article__slug=''
        ).exclude(
            **more_exclude_kwargs
        ).values('article').annotate(total_views=Sum('views')).order_by('-total_views')[:10]
    ]


def mas_leidos_daily(cover=False):
    days_ago = 1 if date.today().isoweekday() < 7 else 2
    return mas_leidos(days_ago, cover)


def mas_leidos_weekly(cover=False):
    return mas_leidos(7, cover)


def mas_leidos_monthly(cover=False):
    return mas_leidos(30, cover)


def masleidos_cover_daily():
    return mas_leidos_daily(True)


def masleidos_cover_weekly():
    return mas_leidos_weekly(True)


def masleidos_cover_monthly():
    return mas_leidos_monthly(True)


@never_cache
@to_response
def index(request):
    return (
        'masleidos_view.html',
        {
            'mas_leidos_daily': mas_leidos_daily(),
            'mas_leidos_weekly': mas_leidos_weekly(),
            'mas_leidos_monthly': mas_leidos_monthly(),
        },
    )


@to_response
def content(request):
    return (
        'masleidos.html',
        {
            'masleidos_cover_daily': masleidos_cover_daily(),
            'masleidos_cover_weekly': masleidos_cover_weekly(),
            'masleidos_cover_monthly': masleidos_cover_monthly(),
        },
    )
