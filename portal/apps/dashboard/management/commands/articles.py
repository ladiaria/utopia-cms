
import os
from os.path import join
import operator
from csv import writer
from progress.bar import Bar

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.urls import resolve
from django.utils.timezone import now, datetime, timedelta

from apps import mongo_db
from core.models import Article, ArticleRel, Section, Publication, ArticleUrlHistory, Category
from signupwall.middleware import get_article_by_url_kwargs


class Command(BaseCommand):
    help = "Generates and rotates the articles report content taking mongodb data for the last month visits"

    def add_arguments(self, parser):
        parser.add_argument(
            "--progress", action="store_true", default=False, dest="progress", help="Show a progress bar"
        )
        parser.add_argument(
            "--live",
            action="store_true",
            default=False,
            dest="live",
            help="Use all mongodb data instead of last month's only",
        )
        parser.add_argument(
            "--out-prefix",
            action="store",
            type=str,
            dest="out-prefix",
            default="",
            help="Don't make changes to existing files and save generated files with this prefix",
        )

    def handle(self, *args, **options):
        if mongo_db is None:
            return

        articles, live, out_prefix = {}, options.get("live"), options.get("out-prefix")
        main_sections, main_categories = {}, {}
        if live and not out_prefix:
            print("ERROR: --live option should also specify a value for --out-prefix option")
            return
        this_month_first = now().date().replace(day=1)
        last_month = this_month_first - timedelta(1)
        last_month_first = datetime.combine(last_month.replace(day=1), datetime.min.time())
        month_before_last = last_month_first - timedelta(1)
        dt_until = datetime.combine(this_month_first, datetime.min.time())

        find_filters = {"user": {"$exists": True}, "path_visited": {"$exists": True}}
        if not live:
            find_filters['timestamp'] = {'$gte': last_month_first, '$lt': dt_until}
        visitors = mongo_db.signupwall_visitor.find(
            find_filters, no_cursor_timeout=settings.MONGODB_NOTIMEOUT_CURSORS_ALLOWED
        )

        verbosity = options.get("verbosity")
        if verbosity > 1:
            if live:
                print("Generating reports ...")
            else:
                print("Generating reports from %s to %s ..." % (last_month_first, dt_until))

        bar = (
            Bar("Processing", max=mongo_db.signupwall_visitor.count_documents(find_filters))
            if options.get("progress")
            else None
        )

        for v in visitors:
            try:

                u = User.objects.get(id=v.get("user"))
                if u.is_staff:
                    continue

                path = v.get("path_visited")
                path_resolved = resolve(path)
                try:
                    article = get_article_by_url_kwargs(path_resolved.kwargs)
                except Article.DoesNotExist:
                    # use url history and search again
                    try:
                        article = ArticleUrlHistory.objects.get(absolute_url=path).article
                    except Exception:
                        continue

                if any([u.subscriber.is_subscriber(p.slug) for p in article.publications()]):
                    viewed = articles.get(u.id, [])
                    viewed.append(article.id)
                    articles[u.id] = viewed
                    index_object = None
                    if article.main_section:
                        section_viewed = main_sections.get(u.id, [])
                        section_viewed.append(article.main_section)
                        main_sections[u.id] = section_viewed
                        if article.main_section.section.slug in getattr(settings, 'DASHBOARD_MAIN_SECTION_SLUGS', []):
                            index_object = article.main_section.section
                        elif article.main_section.section and article.main_section.section.category:
                            index_object = article.main_section.section.category
                        elif (
                            article.main_section.edition.publication
                            and article.main_section.edition.publication.slug
                            not in getattr(settings, "DASHBOARD_EXCLUDE_PUBLICATION_SLUGS", [])
                        ):
                            index_object = article.main_section.edition.publication
                        if index_object:
                            category_viewed = main_categories.get(u.id, [])
                            category_viewed.append(index_object)
                            main_categories[u.id] = category_viewed
            except User.DoesNotExist:
                continue

            finally:
                if bar:
                    bar.next()

            # uncoment this break for fast testing
            # if len(articles):
            #    break

        if settings.MONGODB_NOTIMEOUT_CURSORS_ALLOWED:
            visitors.close()  # needed if created with no_cursor_timeout=True
        if bar:
            bar.finish()

        counters = {}
        for user_id, viewed in articles.items():
            for article_id in viewed:
                counter = counters.get(article_id, 0)
                counter += 1
                counters[article_id] = counter

        sorted_x = sorted(list(counters.items()), key=operator.itemgetter(1), reverse=True)

        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, "articles.csv"),
                join(
                    settings.DASHBOARD_REPORTS_PATH,
                    "%s%.2d_articles.csv" % (month_before_last.year, month_before_last.month),
                ),
            )
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, "%sarticles.csv" % out_prefix), "w"))
        i = 0
        for article_id, score in sorted_x:
            a, category_or_publication = Article.objects.get(id=article_id), ""
            i += 1
            if a.main_section:
                if a.main_section.section and a.main_section.section.category:
                    category_or_publication = a.main_section.section.category
                else:
                    category_or_publication = a.main_section.edition.publication
            pub_section = a.publication_section()
            w.writerow(
                [
                    i,
                    a.get_absolute_url(),
                    a.views,
                    ", ".join(["%s" % ar for ar in a.articlerel_set.all()]),
                    pub_section.name if pub_section else None,
                    category_or_publication,
                    score,
                ]
            )

        # Section
        counters = {}
        for user_id, viewed in main_sections.items():
            for section in viewed:
                ar_id = (section.edition.publication.slug, section.section_id)
                counter = counters.get(ar_id, 0)
                counter += 1
                counters[ar_id] = counter

        sorted_y = sorted(list(counters.items()), key=operator.itemgetter(1), reverse=True)
        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, "sections.csv"),
                join(
                    settings.DASHBOARD_REPORTS_PATH,
                    "%s%.2d_sections.csv" % (month_before_last.year, month_before_last.month),
                ),
            )
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, "%ssections.csv" % out_prefix), "w"))
        i = 0
        for ar_id, score in sorted_y:
            i += 1
            w.writerow([i, Publication.objects.get(slug=ar_id[0]).name, Section.objects.get(pk=ar_id[1]).name, score])

        # Categories and publications
        counters = {}
        for user_id, viewed in iter(main_categories.items()):
            for category in viewed:
                ar_id = (category, category.id)
                counter = counters.get(ar_id, 0)
                counter += 1
                counters[ar_id] = counter

        sorted_y = sorted(counters.items(), key=operator.itemgetter(1), reverse=True)
        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, "categories.csv"),
                join(
                    settings.DASHBOARD_REPORTS_PATH,
                    "%s%.2d_categories.csv" % (month_before_last.year, month_before_last.month),
                ),
            )
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, "%scategories.csv" % out_prefix), "w"))
        i = 0
        for ar_id, score in sorted_y:
            i += 1
            if isinstance(ar_id[0], Category):
                category_or_publication = ar_id[0]
                articles_count = (
                    category_or_publication.articles()
                    .filter(
                        date_published__gte=last_month_first,
                        date_published__lte=dt_until,
                    )
                    .count()
                )
            elif isinstance(ar_id[0], Publication):
                category_or_publication = ar_id[0]
                articles_count = len(
                    set(
                        [
                            ar.article.id for ar in ArticleRel.objects.filter(
                                edition__publication=category_or_publication,
                                article__date_published__gte=last_month_first,
                                article__date_published__lte=dt_until,
                                article__is_published=True,
                            )
                        ]
                    )
                )
            elif isinstance(ar_id[0], Section):
                category_or_publication = ar_id[0]
                articles_count = category_or_publication.articles_core.filter(
                    date_published__gte=last_month_first,
                    date_published__lte=dt_until,
                ).count()
            else:
                continue

            w.writerow([i, category_or_publication.name, articles_count, score, score / (articles_count or 1)])
