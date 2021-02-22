# -*- coding: utf-8 -*-

import sys
from unicodecsv import writer
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Article


class Command(BaseCommand):
    help = 'Writes to stdout a csv with published articles data'

    option_list = BaseCommand.option_list + (
        make_option(
            '--published-from',
            action='store',
            type='string',
            dest='published_from',
            help='Filter by date_published greater than given: YYYY-mm-dd',
        ),
    )

    def handle(self, *args, **options):
        filter_kwargs, published_from = {'is_published': True}, options.get('published_from')
        if published_from:
            filter_kwargs['date_published__gt'] = published_from
        w = writer(sys.stdout)
        w.writerow([
            u'url', u'título', u'fecha', u'hora', u'autores', u'publicación', u'área', u'sección', u'caracteres'])
        for a in Article.objects.filter(**filter_kwargs).order_by('-date_published').iterator():
            ms = a.main_section
            w.writerow([
                a.get_absolute_url(),
                a.headline,
                a.date_published.date(),
                a.date_published.time(),
                u', '.join([x.name for x in a.get_authors()]),
                ms.edition.publication if ms else getattr(a, 'publication', u''),
                ms.section.category if ms else (getattr(a.section, 'category', u'') if a.section else u''),
                ms.section if ms else getattr(a, 'section', u''),
                len(a.body),
            ])
