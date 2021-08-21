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
from core.models import Article, Section, Publication, ArticleUrlHistory
from signupwall.middleware import get_article_by_url_kwargs


class Command(BaseCommand):
    help = 'Generates the articles report content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--progress', action='store_true', default=False, dest='progress', help=u'Show a progress bar'
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

        articles, articlerels, this_month_first = {}, {}, date.today().replace(day=1)
        last_month = this_month_first - timedelta(1)
        last_month_first = datetime.combine(last_month.replace(day=1), datetime.min.time())
        month_before_last = last_month_first - timedelta(1)
        dt_until = datetime.combine(this_month_first, datetime.min.time())

        visitors = signupwall_visitor_mdb.posts.find({
            'timestamp': {'$gte': last_month_first, '$lt': dt_until}, 'user': {'$exists': True},
            'path_visited': {'$exists': True}}, no_cursor_timeout=True)

        verbosity = options.get('verbosity')
        if verbosity > 1:
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
                    articlerels[u.id] = [ar for ar in article.articlerel_set.all()]

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

        out_prefix = options.get('out-prefix')
        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, 'articles.csv'),
                join(settings.DASHBOARD_REPORTS_PATH, '%s%.2d_articles.csv' % (
                    month_before_last.year, month_before_last.month)))
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '%sarticles.csv' % out_prefix), 'w'))
        i = 0
        for article_id, score in sorted_x:
            a = Article.objects.get(id=article_id)
            i += 1
            w.writerow([
                i, a.get_absolute_url(), a.views,
                ', '.join(['%s' % ar for ar in a.articlerel_set.all()]), score])

        counters = {}
        for user_id, articlerels in articlerels.iteritems():
            for articlerel in articlerels:
                ar_id = (articlerel.edition.publication.slug, articlerel.section.id)
                counter = counters.get(ar_id, 0)
                counter += 1
                counters[ar_id] = counter

        sorted_y = sorted(counters.items(), key=operator.itemgetter(1), reverse=True)
        if not out_prefix:
            os.rename(
                join(settings.DASHBOARD_REPORTS_PATH, 'sections.csv'),
                join(settings.DASHBOARD_REPORTS_PATH, '%s%.2d_sections.csv' % (
                    month_before_last.year, month_before_last.month)))
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '%ssections.csv' % out_prefix), 'w'))
        i = 0
        for ar_id, score in sorted_y:
            i += 1
            p = Publication.objects.get(slug=ar_id[0])
            s = Section.objects.get(pk=ar_id[1])
            w.writerow([i, p.name, s.name, score])
