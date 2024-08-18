# -*- coding: utf-8 -*-

import sys
from csv import writer

from django.core.management.base import BaseCommand

from core.models import Article


class Command(BaseCommand):
    help = 'Writes to stdout a csv with published articles data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--published-from',
            action='store',
            type=str,
            dest='published_from',
            help='Filter by date_published greater than given: YYYY-mm-dd',
        )

    def handle(self, *args, **options):
        filter_kwargs, published_from = {'is_published': True}, options.get('published_from')
        if published_from:
            filter_kwargs['date_published__gt'] = published_from
        w = writer(sys.stdout)
        w.writerow(['url', 'título', 'fecha', 'hora', 'autores', 'publicación', 'área', 'sección', 'caracteres'])
        for a in Article.objects.filter(**filter_kwargs).order_by('-date_published').iterator():
            ms = a.main_section
            w.writerow(
                [
                    a.get_absolute_url(),
                    a.headline,
                    a.date_published.date(),
                    a.date_published.time(),
                    ', '.join([x.name for x in a.get_authors()]),
                    ms.edition.publication if ms else getattr(a, 'publication', ''),
                    ms.section.category if ms else (getattr(a.section, 'category', '') if a.section else ''),
                    ms.section if ms else getattr(a, 'section', ''),
                    len(a.body),
                ]
            )
