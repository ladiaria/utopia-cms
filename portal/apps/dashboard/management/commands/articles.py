from __future__ import division

import os
from os.path import join
import operator
from datetime import datetime, date, timedelta
from unicodecsv import writer
from progress.bar import Bar

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.urlresolvers import resolve

from apps import signupwall_visitor_mdb
from core.models import Article, Section, Publication, ArticleUrlHistory, Category
from signupwall.middleware import get_article_by_url_kwargs


class Command(BaseCommand):
    help = 'Generates and rotates the articles report content taking mongodb data for the last month visits'

    def add_arguments(self, parser):
        parser.add_argument(
            '--progress', action='store_true', default=False, dest='progress', help=u'Show a progress bar'
        )
        parser.add_argument(
            '--live',
            action='store_true',
            default=False,
            dest='live',
            help=u"Use all mongodb data instead of last month's only",
        )
        parser.add_argument(
            '--out-prefix',
            action='store',
            type=unicode,
            dest='out-prefix',
            default=u'',
            help=u"Don't make changes to existing files and save generated files with this prefix",
        )

    def handle(self, *args, **options):
        if not signupwall_visitor_mdb:
            return

        articles, main_sections, live, out_prefix = {}, {}, options.get('live'), options.get('out-prefix')
        main_categories = {}
        if live and not out_prefix:
            print(u'ERROR: --live option should also specify a value for --out-prefix option')
            return
        this_month_first = date.today().replace(day=1)
        last_month = this_month_first - timedelta(1)
        last_month_first = datetime.combine(last_month.replace(day=1), datetime.min.time())
        month_before_last = last_month_first - timedelta(1)
        dt_until = datetime.combine(this_month_first, datetime.min.time())

        find_filters = {'user': {'$exists': True}, 'path_visited': {'$exists': True}}
        if not live:
            find_filters['timestamp'] = {'$gte': last_month_first, '$lt': dt_until}
        visitors = signupwall_visitor_mdb.posts.find(find_filters, no_cursor_timeout=True)

        verbosity = options.get('verbosity')
        if verbosity > 1:
            if live:
                print(u'Generating reports ...')
            else:
                print(u'Generating reports from %s to %s ...' % (last_month_first, dt_until))

        bar = Bar('Processing', max=visitors.count()) if options.get('progress') else None

        for v in visitors:
            try:

                u = User.objects.get(id=v.get('user'))
                if u.is_staff:
                    continue

                path = v.get('path_visited')
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
                    if article.main_section:
                        main_sections[u.id] = article.main_section
                        if article.main_section.section and article.main_section.section.category:
                            main_categories[u.id] = article.main_section.section.category
                        elif article.main_section.edition.publication:
                            main_categories[u.id] = article.main_section.edition.publication

            except User.DoesNotExist:
                continue

            finally:
                if bar:
                    bar.next()

            # uncoment this break for fast testing
            # if len(articles):
            #    break

        visitors.close()  # needed because created with no_cursor_timeout=True
        if bar:
            bar.finish()

        counters = {}
        for user_id, viewed in articles.iteritems():
            for article_id in viewed:
                counter = counters.get(article_id, 0)
                counter += 1
                counters[article_id] = counter

        sorted_x = sorted(counters.items(), key=operator.itemgetter(1), reverse=True)

        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, 'articles.csv'),
                join(
                    settings.DASHBOARD_REPORTS_PATH, '%s%.2d_articles.csv' % (
                        month_before_last.year, month_before_last.month
                    )
                ),
            )
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '%sarticles.csv' % out_prefix), 'w'))
        i = 0
        for article_id, score in sorted_x:
            a = Article.objects.get(id=article_id)
            i += 1
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
                    ', '.join(['%s' % ar for ar in a.articlerel_set.all()]),
                    pub_section.name if pub_section else None,
                    category_or_publication,
                    score,
                ]
            )

        counters = {}
        for user_id, main_section in main_sections.iteritems():
            ar_id = (main_section.edition.publication.slug, main_section.section_id)
            counter = counters.get(ar_id, 0)
            counter += 1
            counters[ar_id] = counter

        sorted_y = sorted(counters.items(), key=operator.itemgetter(1), reverse=True)
        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, 'sections.csv'),
                join(
                    settings.DASHBOARD_REPORTS_PATH, '%s%.2d_sections.csv' % (
                        month_before_last.year, month_before_last.month
                    )
                ),
            )
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '%ssections.csv' % out_prefix), 'w'))
        i = 0
        for ar_id, score in sorted_y:
            i += 1
            w.writerow([i, Publication.objects.get(slug=ar_id[0]).name, Section.objects.get(pk=ar_id[1]).name, score])

        # Categories and publications
        counters = {}
        for user_id, main_category in main_categories.iteritems():
            ar_id = (main_category, main_category.id)
            counter = counters.get(ar_id, 0)
            counter += 1
            counters[ar_id] = counter

        sorted_y = sorted(counters.items(), key=operator.itemgetter(1), reverse=True)
        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, 'categories.csv'),
                join(
                    settings.DASHBOARD_REPORTS_PATH, '%s%.2d_categories.csv' % (
                        month_before_last.year, month_before_last.month
                    )
                ),
            )
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '%scategories.csv' % out_prefix), 'w'))
        i = 0
        for ar_id, score in sorted_y:
            i += 1
            if isinstance(ar_id[0], Category):
                category_or_publication = ar_id[0]
                articles_count = category_or_publication.articles().filter(
                    date_published__gte=last_month_first,
                    date_published__lte=dt_until,
                ).count()
            elif isinstance(ar_id[0], Publication):
                articles_count = 0
                category_or_publication = ar_id[0]
                for section in category_or_publication.section_set.all():
                    articles_count += section.articles_core.filter(
                        date_published__gte=last_month_first,
                        date_published__lte=dt_until,
                    ).count()
            else:
                continue

            w.writerow([
                i,
                category_or_publication.name,
                articles_count,
                score,
                score / (articles_count or 1),
            ])
