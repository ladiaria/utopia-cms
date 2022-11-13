# -*- coding: utf-8 -*-
from core.models import Article, Section, Category

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = """
    Changes the category of a section and updates (save all articles whose main section is the one given) url paths
    based on the main_section given.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--section-slug',
            required=True,
            action='store',
            type=str,
            dest='section_slug',
            help='The section slug to be used',
        )
        parser.add_argument(
            '--category-slug',
            required=True,
            action='store',
            type=str,
            dest='category_slug',
            help='The category slug to be used',
        )

    def handle(self, *args, **options):
        s = Section.objects.get(slug=options.get("section_slug"))
        c = Category.objects.get(slug=options.get("category_slug"))
        if s.category != c:
            s.category = c
            s.save()
        for a in Article.published.filter(
            main_section__section=s
        ).exclude(url_path__startswith="/%s/" % c.slug).iterator():
            a.save()
