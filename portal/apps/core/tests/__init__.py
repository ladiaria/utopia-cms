import json
from pathlib import Path

from django.conf import settings
from django.apps import apps
from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.timezone import now

from core.models import Edition, Publication, get_current_edition


base_test_case_class = getattr(settings, 'CORE_TEST_BASE_TEST_CASE_CLASS', TestCase)


# Single source of truth for the fixture that contains the test photo; fixtures list is built from it.
FIXTURE_AND_APP_HOLDING_TEST_IMAGE = ('test.json', 'homev3')


class PreCopyImage(base_test_case_class):

    def precopy_image(self, *args, **kwargs):
        # Used to copy fixture image to storage by hand, this way the image will be available when fixtures are loaded.
        self._test_photo_image_stem = None
        app_config = apps.get_app_config(FIXTURE_AND_APP_HOLDING_TEST_IMAGE[1])
        fixtures_dir = Path(app_config.path) / 'fixtures'
        fixture_json_path = fixtures_dir / FIXTURE_AND_APP_HOLDING_TEST_IMAGE[0]
        if fixture_json_path.exists():
            with open(fixture_json_path, encoding='utf-8') as f:
                for obj in json.load(f):
                    obj_model = obj.get('model')
                    if obj_model == 'photologue.photo':
                        image_path = obj.get('fields', {}).get('image')
                        if image_path:
                            image_path_obj = Path(image_path)
                            self._test_photo_image_stem = image_path_obj.stem
                            source = fixtures_dir / image_path_obj.name
                            if source.exists():
                                precopied, source_content = False, source.read_bytes()
                                do_copy, target_path = True, default_storage.path(image_path)
                                target_path_obj = Path(target_path)

                                if target_path_obj.exists():
                                    existing_target_content = target_path_obj.read_bytes()
                                    if existing_target_content == source_content:
                                        do_copy, precopied = False, True
                                    else:
                                        do_copy = True
                                if do_copy:
                                    default_storage.save(image_path, ContentFile(source_content))
                                    precopied = True
                                if precopied:
                                    break

    def precreate_current_edition(self):
        # Smth similar also happens with the default edition, here we save it before the fixtures are loaded.
        publication, _ = Publication.objects.get_or_create(slug=settings.DEFAULT_PUB)
        Edition.objects.get_or_create(publication=publication, date_published=now().date())

    def _pre_setup(self, *args, **kwargs):
        precreate_current_edition = kwargs.pop('precreate_current_edition', False)
        current_edition = get_current_edition(quiet=True)
        if current_edition:
            precreate_current_edition = False
        if precreate_current_edition:
            self.precreate_current_edition()
        super()._pre_setup(*args, **kwargs)

    def setUp(self, *args, **kwargs):
        self.precopy_image()
        super().setUp(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.precopy_image(*args, **kwargs)
