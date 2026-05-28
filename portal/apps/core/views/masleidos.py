from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.utils.timezone import now, timedelta

from decorators import render_response

from core.models import Article, ArticleRel, ArticleViews, Section
from homev3.views import cache_maxage as homev3_cache_maxage


to_response = render_response('core/templates/')
masleidos_cache_maxage = min(homev3_cache_maxage * 5, 900)
_MASLEIDOS_FULL_CACHE_KEY = 'masleidos_full_content'

# Table names for raw SQL
_ARTICLE_TABLE = Article._meta.db_table
_ARTICLEVIEWS_TABLE = ArticleViews._meta.db_table
_ARTICLEREL_TABLE = ArticleRel._meta.db_table
_SECTION_TABLE = Section._meta.db_table


def mas_leidos(days=1, cover=False, limit=10):
    """
    Returns the top (upto limit) most viewed articles counting days days ago from now.
    If cover is True, articles in satirical sections are excluded. (Issue4910).
    Rare but possible: exclude articles with an empty slug because they will raise exception when computing their urls.
    Uses raw SQL with STRAIGHT_JOIN so the optimizer drives from articleviews (index on day), not from article.
    """
    desde = now().date() - timedelta(days=days)
    satirical = getattr(settings, 'CORE_SATIRICAL_SECTIONS', ()) if cover else ()

    sql = (
        f"SELECT av.article_id, SUM(av.views) AS total_views "
        f"FROM {_ARTICLEVIEWS_TABLE} av "
        f"STRAIGHT_JOIN {_ARTICLE_TABLE} a ON av.article_id = a.id "
        f"WHERE av.day > %s AND a.is_published = 1 AND a.slug != '' "
    )
    params = [desde]

    if satirical:
        # Exclude articles that appear in any satirical section (ArticleRel -> Section)
        placeholders = ', '.join(['%s'] * len(satirical))
        sql += (
            "AND NOT EXISTS ("
            f"SELECT 1 FROM {_ARTICLEREL_TABLE} ar "
            f"INNER JOIN {_SECTION_TABLE} s ON ar.section_id = s.id "
            f"WHERE ar.article_id = a.id AND s.slug IN ({placeholders})) "
        )
        params.extend(satirical)

    sql += "GROUP BY av.article_id ORDER BY total_views DESC LIMIT %s"
    params.append(limit)

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    return [row[0] for row in rows]


def get_articles_by_ids(ids):
    # select_related covers the lazy hits in publication_section (main_section->edition->publication)
    # and prefetch_related covers get_authors (byline M2M) — without these the template triggers
    # 4-6 extra queries per article (N+1) across 3 tabs × 10 articles each.
    qs = Article.objects.filter(id__in=ids).select_related(
        'main_section__edition__publication',
        'main_section__section__category',
    ).prefetch_related('byline')
    articles_by_id = {a.id: a for a in qs}
    return [articles_by_id[aid] for aid in ids if aid in articles_by_id]


def mas_leidos_daily(cover=False, limit=None):
    days_ago = 1 if now().date().isoweekday() < 7 else 2
    return mas_leidos(days_ago, cover, limit) if limit else mas_leidos(days_ago, cover)


def _get_full_content_ids():
    cached = cache.get(_MASLEIDOS_FULL_CACHE_KEY)
    if cached is None:
        cached = {
            'mas_leidos_daily': mas_leidos_daily(),
            'mas_leidos_weekly': mas_leidos(7),
            'mas_leidos_monthly': mas_leidos(30),
        }
        cache.set(_MASLEIDOS_FULL_CACHE_KEY, cached, masleidos_cache_maxage)
    return cached


@cache_page(masleidos_cache_maxage)
def mas_leidos_fullcontent(request):
    return JsonResponse(_get_full_content_ids())


@to_response
def index(request):
    try:
        full_content = {k: get_articles_by_ids(v) for k, v in _get_full_content_ids().items()}
    except Exception:
        full_content = {}

    user = request.user
    if user.is_authenticated:
        all_ids = [a.id for articles in full_content.values() for a in articles]
        follows = [
            int(oid) for oid in user.follow_set.filter(
                content_type=ContentType.objects.get_for_model(Article),
                object_id__in=all_ids,
            ).values_list('object_id', flat=True)
        ]
        full_content['follows'] = follows
        full_content['prefetched_article_data'] = True

    return 'masleidos_view.html', full_content


@cache_page(masleidos_cache_maxage)
@to_response
def content(request):
    return 'masleidos.html', {'masleidos_cover_daily': get_articles_by_ids(mas_leidos_daily(True, 5))}
