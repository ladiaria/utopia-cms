import errno
from os import makedirs
from os.path import isdir, join
import shutil

from django.core.management import BaseCommand
from django.core import serializers
from django.conf import settings

from photologue.models import Photo
from audiologue.models import Audio

from core.models import Article, ArticleRel, Edition, Location, Section


def mkdir_p(path):
    try:
        makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and isdir(path):
            pass
        else:
            raise


class Command(BaseCommand):
    help = 'Dumps the Articles given by id to a JSON set of files.'

    def add_arguments(self, parser):
        parser.add_argument('article_ids', nargs='+', type=int)
        parser.add_argument(
            '--dump-dir',
            action='store',
            type=str,
            dest='dump_dir',
            help='Save generated files in this directory (must exist).',
            default=getattr(settings, 'GENERAL_MANAGEMENT_COMMAND_EXPORT_PATH', '/tmp'),
        )

    def handle(self, *args, **options):
        # TODO: can be optimized writing as many objects as possible of the same type in only one json.
        verbose, dump_dir, photos = options.get('verbosity') > 1, options.get('dump_dir'), []

        for article_id in options.get('article_ids'):
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

            article_dump_file = join(dump_dir, '5article%d.json' % article_id)
            open(article_dump_file, 'w').write(serializers.serialize("json", article_qs))
            if verbose:
                print('wrote ' + article_dump_file)

            article = article_qs[0]
            if article.main_section:
                main_section_edition_dump_file = join(dump_dir, '0article%d_main_section_edition.json' % article_id)
                open(
                    main_section_edition_dump_file, 'w'
                ).write(serializers.serialize("json", Edition.objects.filter(id=article.main_section.edition.id)))
                if verbose:
                    print('wrote ' + main_section_edition_dump_file)

                main_section_section_dump_file = join(dump_dir, '0article%d_main_section_section.json' % article_id)
                open(
                    main_section_section_dump_file, 'w'
                ).write(serializers.serialize("json", Section.objects.filter(id=article.main_section.section.id)))
                if verbose:
                    print('wrote ' + main_section_section_dump_file)

                main_section_dump_file = join(dump_dir, '1article%d_main_section.json' % article_id)
                open(
                    main_section_dump_file, 'w'
                ).write(serializers.serialize("json", ArticleRel.objects.filter(id=article.main_section.id)))
                if verbose:
                    print('wrote ' + main_section_dump_file)

            if article.extensions.exists():
                extensions_dump_file = join(dump_dir, 'article%d_extensions.json' % article_id)
                open(extensions_dump_file, 'w').write(serializers.serialize("json", article.extensions.all()))
                if verbose:
                    print('wrote ' + extensions_dump_file)

            if article.photo:
                photo_dump_file = join(dump_dir, '4article%d_photo.json' % article_id)
                open(
                    photo_dump_file, 'w'
                ).write(serializers.serialize("json", Photo.objects.filter(id=article.photo.id)))
                photos.append(article.photo.image.path)
                if verbose:
                    print('wrote ' + photo_dump_file)

            if article.audio:
                audio_dump_file = join(dump_dir, '4article%d_audio.json' % article_id)
                open(
                    audio_dump_file, 'w'
                ).write(serializers.serialize("json", Audio.objects.filter(id=article.audio.id)))
                if verbose:
                    print('wrote ' + audio_dump_file)

            if article.location:
                location_dump_file = join(dump_dir, '4article%d_location.json' % article_id)
                open(
                    location_dump_file, 'w'
                ).write(serializers.serialize("json", Location.objects.filter(id=article.location.id)))
                if verbose:
                    print('wrote ' + location_dump_file)

            if article.body_image.exists():
                bodyimages_photos_dump_file = join(dump_dir, '2article%d_bodyimages_photos.json' % article_id)
                open(
                    bodyimages_photos_dump_file, 'w'
                ).write(
                    serializers.serialize(
                        "json", Photo.objects.filter(id__in=article.body_image.values_list('image', flat=True))
                    )
                )
                photos.extend(body_img.image.image.path for body_img in article.body_image.all())
                if verbose:
                    print('wrote ' + bodyimages_photos_dump_file)
                bodyimages_dump_file = join(dump_dir, '3article%d_bodyimages.json' % article_id)
                open(bodyimages_dump_file, 'w').write(serializers.serialize("json", article.body_image.all()))
                if verbose:
                    print('wrote ' + bodyimages_dump_file)

        if photos:
            photos_dump_dir = join(dump_dir, 'photos')
            mkdir_p(photos_dump_dir)
            for photo_path in photos:
                shutil.copy(photo_path, photos_dump_dir)

        if verbose:
            print('Done. Use loaddata command to import the generated files, if any.')
