import errno
from os import makedirs
from os.path import isdir, join, exists
import shutil
import json
from pprint import pprint
from actstream.models import Action

from django.conf import settings
from django.core import serializers
from django.core.management import BaseCommand, CommandError
from django.db.models.deletion import Collector

from core.models import (
    Article,
    ArticleRel,
    CategoryHome,
    ArticleBodyImage,
    CategoryHomeArticle,
    PushNotification,
    ArticleViewedBy,
    ArticleViews,
)


def mkdir_p(path):
    try:
        makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and isdir(path):
            pass
        else:
            raise


class Command(BaseCommand):
    help = 'Dumps the Articles given by id or filter expression to a JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('article_ids', nargs='*', type=int, help="takes precedence over --filter-kwargs")
        parser.add_argument(
            '--filter-kwargs',
            action="store",
            dest="filter_kwargs",
            type=str,
            help="json of dict to be used as kwargs in the filtered dump",
        )
        parser.add_argument(
            '--dump-dir',
            action='store',
            type=str,
            dest='dump_dir',
            help='Save generated files in this directory (must exist).',
            default=getattr(settings, 'GENERAL_MANAGEMENT_COMMAND_EXPORT_PATH', '/tmp'),
        )

    def handle(self, *args, **options):
        # TODO: dump also audio media files (not only photos)
        verbose, dump_dir, photos = options.get('verbosity') > 1, options.get('dump_dir'), []
        try:
            article_ids, filter_kwargs = options.get('article_ids'), json.loads(options.get('filter_kwargs') or "{}")
            assert article_ids or filter_kwargs, "At least one Article id or the filter json must be given"
        except (ValueError, AssertionError) as va_err:
            raise CommandError(va_err)

        to_collect = []
        article_ids = options.get('article_ids')
        dump_source = article_ids if article_ids else Article.objects.filter(**filter_kwargs)
        for article_ref in dump_source:
            if type(article_ref) is int:
                article_id = article_ref
                try:
                    article_qs = Article.objects.filter(id=article_id)
                except (IndexError, ValueError):
                    if verbose:
                        print("%s - Wrong parameter" % article_id)
                    continue
                if not article_qs.exists():
                    if verbose:
                        print("%s - Article not found" % article_id)
                    continue
            else:
                article_qs = [article_ref]

            article = article_qs[0]
            to_collect.append(article)

            if article.photo:
                photos.append(article.photo.image.path)
            if article.body_image.exists():
                photos.extend(body_img.image.image.path for body_img in article.body_image.all())

        if photos:
            photos_dump_dir = join(dump_dir, 'photos')
            mkdir_p(photos_dump_dir)
            for photo_path in photos:
                if exists(photo_path):
                    shutil.copy(photo_path, photos_dump_dir)

        collector = Collector(using='default')
        collector.collect(to_collect)
        todump = set()
        for key in collector.data.keys():
            if key in (PushNotification, ArticleViewedBy, ArticleViews, Action):
                continue
            for obj in collector.data[key]:
                if key is CategoryHomeArticle:
                    if obj.home:
                        todump.add(obj.home)
                elif key is CategoryHome:
                    todump.add(obj.category)
                elif key is ArticleBodyImage:
                    todump.add(obj.image)
                elif key is Article:
                    for subset in (
                        obj.get_authors(),
                        obj.extensions.all(),
                        obj.body_image.all(),
                        set([x for x in (obj.photo, obj.audio, obj.location) if x]),
                    ):
                        todump = todump.union(subset)
                elif key is ArticleRel:
                    for subset in (
                        set([obj.edition, obj.edition.publication, obj.section]), obj.section.publications.all()
                    ):
                        todump = todump.union(subset)
                    if obj.section.category:
                        todump.add(obj.section.category)
                todump.add(obj)
        if verbose:
            print("Dumping all objects in the following set to a single dump file:")
            pprint(todump)
        serialized_data = serializers.serialize(
            "json", todump, indent=2, use_natural_foreign_keys=True, use_natural_primary_keys=True
        )
        dump_file = join(dump_dir, 'dump.json')
        open(dump_file, 'w').write(serialized_data)
        if verbose:
            print('wrote ' + dump_file)
            print('Done. Use loaddata command to import the generated files, if any.')
