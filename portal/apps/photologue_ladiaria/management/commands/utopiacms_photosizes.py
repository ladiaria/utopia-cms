from django.core.management import BaseCommand

from photologue.models import PhotoSize


class Command(BaseCommand):
    help = """ Creates the photosizes needed by utopia-cms (if not already created) """

    def handle(self, *args, **options):
        print('Creating utopia-cms PhotoSizes (if not already created, searching for existing only by name).')

        sizes_vary_width = {
            '1200w': 1200,
            '700w': 700,
            '250w': 250,
            '350w': 350,
            '450w': 450,
            '600w': 600,
            'article_main': 833,
            '900w': 900,
            'med': 1170,
            '1192w': 1192,
            '1440w': 1440,
            '1920w': 1920,
            'fullscreen': 2000,
        }

        for name, width in sizes_vary_width.iteritems():
            if not PhotoSize.objects.filter(name=name).exists():
                PhotoSize.objects.create(
                    name=name, width=width, height=0, crop=False, pre_cache=False, increment_count=False)

        # other sizes with special attrs
        if not PhotoSize.objects.filter(name='article_thumb').exists():
            PhotoSize.objects.create(
                name='article_thumb', width=180, height=180, crop=False, pre_cache=True, increment_count=False)
        if not PhotoSize.objects.filter(name='cover_landscape').exists():
            PhotoSize.objects.create(
                name='cover_landscape',
                width=1200,
                height=0,
                crop=False,
                pre_cache=False,
                increment_count=False,
                quality=80,
            )
