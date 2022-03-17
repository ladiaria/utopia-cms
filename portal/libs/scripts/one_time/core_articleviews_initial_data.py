from datetime import date

from apps import core_articleviewedby_mdb

from core.models import Article, ArticleViews


articles, upto = {}, date(2022, 3, 14)

for avb in core_articleviewedby_mdb.posts.find():
    va = avb['viewed_at'].date()
    if va < upto:
        article = avb['article']
        dates = articles.get(article, {})
        if dates or Article.objects.filter(id=article).exists():
            views = dates.get(va, 0)
            views += 1
            dates[va] = views
            articles[article] = dates

ArticleViews.objects.bulk_create(
    ArticleViews(article_id=article, day=d, views=v) for article, dates in articles.items() for d, v in dates.items()
)
