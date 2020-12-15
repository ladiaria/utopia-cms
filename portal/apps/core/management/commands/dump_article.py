import sys
from os.path import join

from django.core.management import BaseCommand
from django.core import serializers
from django.conf import settings

from core.models import Article


class Command(BaseCommand):
    args = '<article_id>'
    help = 'Dumps the Article given by id to a JSON set of files.'

    def handle(self, *args, **options):
        dump_path = getattr(
            settings, 'GENERAL_MANAGEMENT_COMMAND_EXPORT_PATH', '/tmp')
        try:
            article_id = int(args[0])
            article_qs = Article.objects.filter(id=article_id)
        except (IndexError, ValueError):
            sys.exit("Wrong parameter")
        if not article_qs.exists():
            sys.exit("Article not found")

        article_dump_file = join(dump_path, 'article%d.json' % article_id)
        open(article_dump_file, 'w').write(
            serializers.serialize("json", article_qs))
        print('wrote ' + article_dump_file)

        article = article_qs[0]
        if article.extensions.exists():
            extensions_dump_file = join(
                dump_path, 'article%d_extensions.json' % article_id)
            open(extensions_dump_file, 'w').write(
                serializers.serialize("json", article.extensions.all()))
            print('wrote ' + extensions_dump_file)

        if article.body_image.exists():
            images_dump_file = join(
                dump_path, 'article%d_images.json' % article_id)
            open(images_dump_file, 'w').write(
                serializers.serialize("json", article.body_image.all()))
            print('wrote ' + images_dump_file)

        print('Done. Use loaddata command to import the generated files.')
