from django.conf import settings
from django.db import connection
from django.views.decorators.cache import never_cache, cache_page
from django.utils.timezone import now, timedelta

from decorators import render_response

from core.models import Article, ArticleRel, ArticleViews, Section


to_response = render_response('core/templates/')

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

    ids = [row[0] for row in rows]
    if not ids:
        return []
    articles_by_id = {a.id: a for a in Article.objects.filter(id__in=ids)}
    return [articles_by_id[aid] for aid in ids if aid in articles_by_id]


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


@cache_page(900)
@to_response
def content(request):
    return 'masleidos.html', {'masleidos_cover_daily': mas_leidos_daily(True, 5)}
