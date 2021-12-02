from os.path import join
from unicodecsv import writer
import operator
from progress.bar import Bar

from django.core.management.base import BaseCommand
from django.conf import settings

from core.models import Article, ArticleViewedBy, Publication, Section


class Command(BaseCommand):
    help = u'Generates the articles report content for subscribers visits'

    def add_arguments(self, parser):
        parser.add_argument(
            '--progress', action='store_true', default=False, dest='progress', help=u'Show a progress bar'
        )
        parser.add_argument(
            '--published-since',
            action='store',
            type=unicode,
            dest='published-since',
            help='Only count visits of articles published at or after this date, in format : YYYY-mm-dd',
        )
        parser.add_argument(
            '--views-since',
            action='store',
            type=unicode,
            dest='views-since',
            help='Only count visits at or after this date, in format : YYYY-mm-dd',
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
        published_since, views_since = options.get('published-since'), options.get('views-since')

        filter_articles_kwargs = {'is_published': True, 'views__gt': 0}
        filter_views_kwargs = {'user__is_staff': False, 'user__subscriber__isnull': False}

        if published_since:
            filter_articles_kwargs.update({'date_published__gte': published_since})

        if views_since:
            filter_views_kwargs.update({'viewed_at__gte': views_since})

        verbosity = options.get('verbosity')
        if verbosity > '1':
            gen_msg = u'Generating reports for articles published '
            gen_msg += ((u'since %s' % published_since) if published_since else u'on any date') + u' and views '
            print(gen_msg + ((u'since %s' % views_since) if views_since else u'on any date')) + u' ...'

        target_articles, articles, articles_sections = Article.objects.filter(**filter_articles_kwargs), [], {}
        bar = Bar('Processing articles', max=target_articles.count()) if options.get('progress') else None

        for article in target_articles.select_related('main_section__edition').iterator():
            filter_views_kwargs.update({'article': article})
            views, digital_views, article_publications = 0, 0, article.publications()

            for article_view in ArticleViewedBy.objects.select_related(
                'user__subscriber'
            ).filter(**filter_views_kwargs).iterator():

                if (
                    article_view.user.subscriber.is_subscriber()
                    or any([article_view.user.subscriber.is_subscriber(p.slug) for p in article_publications])
                ):
                    views += 1
                    if article_view.user.subscriber.is_digital_only():
                        digital_views += 1

            if views:
                articles.append((article.id, views, digital_views))

                main_section = article.main_section
                if main_section:
                    main_publication_id = main_section.edition.publication_id
                    main_section_id = main_section.section_id
                    section_views, section_digital_views = articles_sections.get(
                        (main_publication_id, main_section_id), (0, 0)
                    )
                    section_views += views
                    section_digital_views += digital_views
                    articles_sections[(main_publication_id, main_section_id)] = (section_views, section_digital_views)

            if bar:
                bar.next()

        if bar:
            bar.finish()

        articles.sort(key=operator.itemgetter(1), reverse=True)

        out_prefix = options.get('out-prefix')

        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '%ssubscribers.csv' % out_prefix), 'w'))
        i = 0
        for article_id, views, digital_views in articles:
            article = Article.objects.get(id=article_id)
            i += 1
            w.writerow(
                [
                    i,
                    article.date_published.date(),
                    article.get_absolute_url(),
                    views,
                    digital_views,
                    ', '.join(['%s' % ar for ar in article.articlerel_set.all()]),
                ]
            )

        as_list = [(p, s, v, dv) for (p, s), (v, dv) in articles_sections.iteritems()]
        as_list.sort(key=operator.itemgetter(2), reverse=True)
        w = writer(open(join(settings.DASHBOARD_REPORTS_PATH, '%ssubscribers_sections.csv' % out_prefix), 'w'))
        i = 0
        for publication_id, section_id, views, digital_views in as_list:
            i += 1
            w.writerow(
                [
                    i,
                    Publication.objects.get(id=publication_id).name,
                    Section.objects.get(id=section_id).name,
                    views,
                    digital_views,
                ]
            )
