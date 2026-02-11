from time import time
import operator
from copy import copy

from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils.timezone import now, timedelta

from .models import Category, ArticleRel, Section, Edition, CategoryHome, CategoryHomeArticle


def update_category_home(categories=settings.CORE_UPDATE_CATEGORY_HOMES, dry_run=False, sql_debug=False):
    """
    Updates categories homes based on articles publishing dates
    """
    all_with_home = Category.objects.filter(home__isnull=False)
    # override empty list to "all" if "all" is configured by settings
    if not categories and getattr(settings, 'CORE_UPDATE_CATEGORY_HOMES_ALL_HOMES', False):
        categories = all_with_home
    else:
        categories = all_with_home.filter(slug__in=categories)
    # fill each category bucket with latest articles.
    # @dry_run: Do not change anything. It forces a debug message when a change would be made.
    # TODO: calculate not fixed count before and better stop algorithm.
    buckets, category_sections, cat_needed_defaults, cat_needed, start_time, result = {}, {}, {}, {}, time(), []
    categories_to_fill = []

    for cat in categories:
        needed = getattr(
            settings, 'CORE_UPDATE_CATEGORY_HOMES_ARTICLES_NEEDED', {}
        ).get(cat.slug, getattr(settings, 'CORE_UPDATE_CATEGORY_HOMES_ARTICLES_NEEDED_DEFAULT', 10))
        cat_needed_defaults[cat.slug] = needed
        exclude_sections = getattr(settings, 'CORE_UPDATE_CATEGORY_HOMES_EXCLUDE_SECTIONS', {}).get(cat.slug, [])
        articles_count = cat.articles_count(needed, exclude_sections, sql_debug)
        include_extra_sections = getattr(settings, 'CORE_UPDATE_CATEGORY_HOMES_INCLUDE_EXTRA_SECTIONS', {}).get(
            cat.slug, []
        )

        # NOTICE: tag exclude filtering (if defined by settings) is ignored to evaluate this needed limits
        if articles_count < needed and include_extra_sections:
            articles_count += ArticleRel.articles_count(needed - articles_count, include_extra_sections, sql_debug)

        if articles_count:
            categories_to_fill.append(cat.slug)
            buckets[cat.slug], cat_needed[cat.slug] = [], articles_count
            category_sections[cat.slug] = set(
                list(cat.section_set.values_list('id', flat=True))
                + (
                    list(Section.objects.filter(slug__in=include_extra_sections).values_list('id', flat=True))
                    if include_extra_sections
                    else []
                )
            ) - set(
                Section.objects.filter(slug__in=exclude_sections).values_list('id', flat=True)
                if exclude_sections
                else []
            )

    if categories_to_fill:
        if settings.DEBUG:
            result.append('DEBUG: update_category_home begin')

        lowest_date, max_date = Edition.objects.last().date_published, now().date()
        days_step = getattr(settings, 'CORE_UPDATE_CATEGORY_HOMES_DAYS_STEP', 30)
        exclude_tags = getattr(settings, 'CORE_UPDATE_CATEGORY_HOMES_EXCLUDE_TAGS', {})
        min_date_iter, max_date_iter, stop = max_date - timedelta(days_step), max_date, False

        while max_date_iter > lowest_date:

            for ar in (
                ArticleRel.objects.select_related('article', 'edition')
                .filter(edition__date_published__range=(min_date_iter, max_date_iter), article__is_published=True)
                .order_by('-edition__date_published', '-article__date_published')
                .iterator()
            ):

                if categories_to_fill:
                    # insert the article (if matches criteria) limiting upto needed quantity with no dupe articles
                    article = ar.article
                    for cat_slug in categories_to_fill:
                        if (
                            article not in [x[0] for x in buckets[cat_slug]]
                            and ar.section_id in category_sections[cat_slug]
                            and not (
                                cat_slug in exclude_tags
                                and any(slugify(t.name) in exclude_tags[cat_slug] for t in article.get_tags())
                            )
                        ):
                            buckets[cat_slug].append((article, (ar.edition.date_published, article.date_published)))
                            if len(buckets[cat_slug]) == cat_needed[cat_slug]:
                                categories_to_fill.remove(cat_slug)
                else:
                    stop = True
                    break

            if stop:
                break
            else:
                max_date_iter = min_date_iter - timedelta(1)
                min_date_iter = max_date_iter - timedelta(days_step)

    # iterate over the buckets and compute free places to fill
    for category_slug, articles in list(buckets.items()):
        category = categories.get(slug=category_slug)

        try:
            home = category.home
        except CategoryHome.DoesNotExist:
            continue

        try:
            home_cover = CategoryHomeArticle.objects.get(home=home, position=1)
        except CategoryHomeArticle.DoesNotExist:
            home_cover = None
        cover_id = home_cover.article_id if home_cover else None
        cover_fixed = home_cover.fixed if home_cover else False
        category_fixed_content, free_places = ([cover_id], []) if cover_fixed else ([], [0])

        try:
            for i in range(2, cat_needed_defaults[category_slug] + 1):
                try:
                    position_i = CategoryHomeArticle.objects.get(home=home, position=i)
                    a = position_i.article
                    aid, afixed = a.id, position_i.fixed
                    if afixed:
                        category_fixed_content.append(aid)
                    else:
                        free_places.append(i)
                except CategoryHomeArticle.DoesNotExist:
                    free_places.append(i)

        except IndexError:
            pass

        # if not free places nothing will be done, then continue
        if not free_places:
            continue

        # make list with the new articles based on the free places
        free_places2, category_content = copy(free_places), []
        for article, date_published_tuple in articles:

            if article.id in category_fixed_content:
                continue

            # append in category_content to be reordered later
            category_content.append((free_places.pop(), date_published_tuple, article))

            if not len(free_places):
                break

        # sort new articles
        category_content.sort(key=operator.itemgetter(1), reverse=True)

        # update the content
        for i, ipos in enumerate(free_places2):

            try:
                old_pos, date_pub, art = category_content[i]

                if ipos:
                    if settings.DEBUG or dry_run:
                        result.append('DEBUG: update %s home position %d: %s' % (home.category, ipos, art))
                    if not dry_run:
                        home.set_article(art, ipos)
                else:
                    if settings.DEBUG or dry_run:
                        result.append('DEBUG: update %s home cover: %s' % (home.category, art))
                    if not dry_run:
                        home.set_article(art, 1)
            except IndexError:
                pass

    if settings.DEBUG:
        result.append('DEBUG: update_category_home completed in %.0f seconds' % (time() - start_time))
    return "\n".join(result)
