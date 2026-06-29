from django.core.management import BaseCommand

from photologue.models import PhotoSize


class Command(BaseCommand):
    help = "Creates the photosizes needed by utopia-cms (if not already created)"

    def handle(self, *args, **options):
        print('Creating utopia-cms PhotoSizes (if not already created, searching for existing only by name).')

        sizes_vary_width = {
            '1200w': 1200,
            '700w': 700,
            '250w': 250,
            '350w': 350,
            '450w': 450,
            '600w': 600,
            'article_main': 1200,
            '900w': 900,
            'med': 1170,
            '1192w': 1192,
            '1440w': 1440,
            '1920w': 1920,
            'fullscreen': 2000,
        }

        for name, width in sizes_vary_width.items():
            if not PhotoSize.objects.filter(name=name).exists():
                ps = PhotoSize.objects.create(
                    name=name, width=width, height=0, crop=False, pre_cache=False, increment_count=False
                )
                if name in ("450w", "700w"):
                    ps.quality = 90
                    ps.save()

        # other size with special attrs
        if not PhotoSize.objects.filter(name='article_thumb').exists():
            PhotoSize.objects.create(
                name='article_thumb', width=180, height=180, crop=False, pre_cache=False, increment_count=False
            )

        # image for the article structured data (JSON-LD). Google Discover requires it to be at least
        # 1200px wide, so this size upscales smaller source images instead of returning them as-is.
        if not PhotoSize.objects.filter(name='schema_image').exists():
            PhotoSize.objects.create(
                name='schema_image', width=1200, height=0, crop=False, upscale=True, pre_cache=False,
                increment_count=False
            )
