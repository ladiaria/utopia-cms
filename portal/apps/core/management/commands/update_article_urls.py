# -*- coding: utf-8 -*-
# utopia-cms 2024. Aníbal Pacheco.


from tqdm import tqdm

from django.conf import settings
from django.core.management import BaseCommand

from core.models import Publication, Article


def update_article_urls(pub_slugs, verbose=False):
    filter_kwargs, errors, saved = {"slug__in": pub_slugs} if pub_slugs else {}, [], 0
    for p in Publication.objects.filter(**filter_kwargs):
        for a in tqdm(Article.objects.filter(main_section__edition__publication=p), disable=not verbose):
            try:
                a.save()
            except Exception as exc:
                errors.append((a.id, exc))
            else:
                saved += 1

    result = "%d articles saved" % saved
    if errors:
        result += "\nErrors:\n" + "\n".join([" * Article %d: %s" % (a_id, exc) for a_id, exc in errors])
    return result


class Command(BaseCommand):
    help = "Updates (saves) all articles that are 'main' published in the publications given by slug (or all pubs)"

    def add_arguments(self, parser):
        parser.add_argument('publication_slugs', nargs="*", type=str)

    def handle(self, *args, **options):
        pub_slugs, verbose = options.get("publication_slugs"), options.get("verbosity") > 1
        result = update_article_urls(pub_slugs, verbose)
        if verbose or settings.DEBUG:
            print(result)
