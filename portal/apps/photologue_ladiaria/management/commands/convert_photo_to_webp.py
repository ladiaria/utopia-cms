import logging

from django.core.management import BaseCommand
from photologue.models import Photo

from ...utils import convert_photo_image_to_webp


class Command(BaseCommand):
    help = (
        "Convert photo(s) to WebP (by format, not filename). "
        "Pass one or more photo IDs (space-separated), or use --from-id/--to-id for a range, "
        "or omit everything to convert all (prompts for confirmation unless --noinput). "
        "If --from-id or --to-id is given, explicit IDs are ignored; missing end = unbounded."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'photo_id',
            type=int,
            nargs='*',
            help='ID(s) of the Photo to convert (space-separated). Ignored if --from-id/--to-id is used.',
        )
        parser.add_argument(
            '--from-id',
            type=int,
            default=None,
            metavar='ID',
            help='Convert photos with pk >= this (range mode; ignores positional IDs). Omit for -inf.',
        )
        parser.add_argument(
            '--to-id',
            type=int,
            default=None,
            metavar='ID',
            help='Convert photos with pk <= this (range mode; ignores positional IDs). Omit for +inf.',
        )
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_true',
            dest='no_input',
            help='Do not prompt for confirmation when converting all photos.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only report what would be converted, do not save.',
        )
        parser.add_argument(
            '--progress',
            action='store_true',
            help='Show progress bar with tqdm.',
        )

    def handle(self, *args, **options):
        photo_ids = options['photo_id']
        from_id = options['from_id']
        to_id = options['to_id']
        no_input = options['no_input']
        dry_run = options['dry_run']
        progress = options.get('progress', False)

        use_range = from_id is not None or to_id is not None
        if use_range:
            queryset = self._range_queryset(from_id, to_id)
            need_confirm = False
        elif photo_ids:
            queryset = Photo.objects.filter(pk__in=photo_ids).order_by('pk')
            need_confirm = False
        else:
            queryset = Photo.objects.all().order_by('pk')
            need_confirm = True

        verbosity = options.get('verbosity', 1)
        if need_confirm and not no_input and not dry_run:
            if not self._confirm_all():
                if verbosity >= 1:
                    self.stdout.write('Aborted.')
                return

        if verbosity < 2:
            utils_log = logging.getLogger('photologue_ladiaria.utils')
            old_level = utils_log.level
            utils_log.setLevel(logging.CRITICAL)
            try:
                self._convert_queryset(
                    queryset, dry_run=dry_run, verbosity=verbosity, progress=progress
                )
            finally:
                utils_log.setLevel(old_level)
        else:
            self._convert_queryset(
                queryset, dry_run=dry_run, verbosity=verbosity, progress=progress
            )

    def _range_queryset(self, from_id, to_id):
        """Build queryset for pk in [from_id, +inf], [-inf, to_id], or [from_id, to_id]."""
        q = Photo.objects.all()
        if from_id is not None:
            q = q.filter(pk__gte=from_id)
        if to_id is not None:
            q = q.filter(pk__lte=to_id)
        return q.order_by('pk')

    def _convert_queryset(self, queryset, dry_run=False, verbosity=1, progress=False):
        if verbosity >= 2 and dry_run:
            self.stdout.write('Dry run: no changes will be saved.')

        total = 0
        converted = 0

        if progress:
            try:
                from tqdm import tqdm
            except ImportError:
                self.stderr.write(self.style.WARNING('tqdm not installed; --progress ignored.'))
                progress = False

        it = queryset.iterator()
        if progress:
            count = queryset.count()
            it = tqdm(it, total=count, unit='photo', desc='Converting')

        for photo in it:
            total += 1
            if dry_run:
                try:
                    from PIL import Image
                    with Image.open(photo.image) as img:
                        if getattr(img, 'format', None) != 'WEBP':
                            converted += 1
                            if verbosity >= 2:
                                self.stdout.write(
                                    'Would convert: Photo id=%s title=%s' % (photo.pk, photo.title)
                                )
                except Exception as e:
                    if verbosity >= 2:
                        self.stderr.write(self.style.WARNING('Photo id=%s: %s' % (photo.pk, e)))
            else:
                if convert_photo_image_to_webp(photo):
                    converted += 1
                    if verbosity > 2:
                        self.stdout.write('Converted: Photo id=%s' % photo.pk)

        if verbosity >= 1:
            self.stdout.write(
                self.style.SUCCESS('Done. Total=%s, converted=%s.' % (total, converted))
            )

    def _confirm_all(self):
        """Return True if the user confirms converting all photos."""
        return input('Convert ALL photos to WebP? [y/N]: ').strip().lower() in ('y', 'yes')
