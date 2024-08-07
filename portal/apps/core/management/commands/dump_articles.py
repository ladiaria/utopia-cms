import errno
from os import makedirs
from os.path import isdir, join, exists
import shutil
import json
from pprint import pprint
from actstream.models import Action
from photologue.models import Photo, Gallery

from django.conf import settings
from django.core import serializers
from django.core.management import BaseCommand, CommandError
from django.db.models.deletion import Collector

from core.models import (
    Publication,
    Article,
    ArticleRel,
    CategoryHome,
    ArticleBodyImage,
    CategoryHomeArticle,
    PushNotification,
    ArticleViewedBy,
    ArticleViews,
    Edition,
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
    help = """
        Dumps the Articles given by id or filter expression to a JSON file, the generated file can then be loaded
        using `loaddata` command.
        The command will also copy all images related to the articles beeing dumped to the `photos` subdirectory under
        the dump directory that was given to the command by argument.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            'article_ids',
            nargs='*',
            type=int,
            help="Article IDs separated by space, takes precedence over `--filter-kwargs`.",
        )
        parser.add_argument(
            '--filter-kwargs',
            action="store",
            dest="filter_kwargs",
            type=str,
            default="{}",
            help="A dict in JSON format, it will be passed as `**kwargs` to `Article.filter()` to obtain the set to "
                 "be dumped.",
        )
        parser.add_argument(
            '--dump-dir',
            action='store',
            type=str,
            dest='dump_dir',
            help='Save generated dump.json file and copy images to this directory.',
            default=getattr(settings, 'GENERAL_MANAGEMENT_COMMAND_EXPORT_PATH', '/tmp'),
        )

    def handle(self, *args, **options):
        # TODO: dump also audio media files (not only photos)
        #       filter may also be used to filter the ids given
        verbose, dump_dir = options.get('verbosity') > 1, options.get('dump_dir')
        try:
            filter_kwargs = json.loads(options.get('filter_kwargs'))
        except ValueError as v_err:
            raise CommandError(v_err)

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

        collector = Collector(using='default')
        collector.collect(to_collect)

        todump = set()
        publications = set(collector.data.pop(Publication, []))
        editions = set(collector.data.pop(Edition, []))
        galleries = set(collector.data.pop(Gallery, []))
        photos = set(collector.data.pop(Photo, []))

        for key in collector.data.keys():
            if key in (PushNotification, ArticleViewedBy, ArticleViews, Action, Article.byline.through):
                continue
            for obj in collector.data[key]:
                if key is CategoryHomeArticle:
                    if obj.home:
                        todump.add(obj.home)
                elif key is CategoryHome:
                    todump.add(obj.category)
                elif key is ArticleBodyImage:
                    photos.add(obj.image)
                elif key is Article:
                    for subset in (
                        obj.get_authors(),
                        obj.extensions.all(),
                        obj.body_image.all(),
                        set([x for x in (obj.audio, obj.location) if x]),
                    ):
                        todump = todump.union(subset)
                    if obj.photo:
                        photos.add(obj.photo)
                    if obj.body_image.exists():
                        photos = photos.union(set([body_img.image for body_img in article.body_image.all()]))
                    if obj.gallery:
                        galleries.add(obj.gallery)
                elif key is ArticleRel:
                    publications.add(obj.edition.publication)
                    publications = publications.union(obj.section.publications.all())
                    editions.add(obj.edition)
                    todump.add(obj.section)
                    if obj.section.category:
                        todump.add(obj.section.category)
                todump.add(obj)

        for obj in publications:
            if obj.full_width_cover_image:
                photos.add(obj.full_width_cover_image)

        for obj in galleries:
            photos = photos.union(obj.photos.all())

        if photos:
            photos_dump_dir = join(dump_dir, 'photos')
            mkdir_p(photos_dump_dir)
            for photo in photos:
                if exists(photo.image.path):
                    shutil.copy(photo.image.path, photos_dump_dir)

        if verbose:
            print("Dumping all objects in the following sets to a single dump file:")
            pprint((photos, galleries, publications, editions, todump))

        serialized_data = json.loads(
            serializers.serialize("json", photos, use_natural_foreign_keys=True, use_natural_primary_keys=True)
        ) + json.loads(
            serializers.serialize("json", galleries, use_natural_foreign_keys=True, use_natural_primary_keys=True)
        )

        # drop site info from photos and galleries (probably never match in load environment)
        for entry in serialized_data:
            entry["fields"].pop("sites")

        serialized_data += json.loads(
            serializers.serialize("json", publications, use_natural_foreign_keys=True, use_natural_primary_keys=True)
        ) + json.loads(
            serializers.serialize("json", editions, use_natural_foreign_keys=True, use_natural_primary_keys=True)
        ) + json.loads(
            serializers.serialize("json", todump, use_natural_foreign_keys=True, use_natural_primary_keys=True)
        )

        # and write result file dump
        dump_file_path = join(dump_dir, 'dump.json')
        dump_file_obj = open(dump_file_path, 'w')
        dump_file_obj.write(json.dumps(serialized_data))
        dump_file_obj.close()
        if verbose:
            print('wrote ' + dump_file_path)
            print('Done. Use loaddata command to import the generated files, if any.')
