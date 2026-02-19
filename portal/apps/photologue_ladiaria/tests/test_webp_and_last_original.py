# -*- coding: utf-8 -*-
"""
Tests for WebP conversion and last_original_uploaded at model save level.
No browser; at most Django test client for URL asserts if needed.
"""
import re
from io import BytesIO

from PIL import Image
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from photologue.models import Photo


def make_jpg_bytes(color='red', size=(10, 10)):
    buf = BytesIO()
    img = Image.new('RGB', size, color=color)
    img.save(buf, format='JPEG')
    return buf.getvalue()


def make_webp_bytes(color='blue', size=(10, 10)):
    buf = BytesIO()
    img = Image.new('RGB', size, color=color)
    img.save(buf, format='WEBP')
    return buf.getvalue()


def get_last_original_content(photo):
    if not hasattr(photo, 'extended') or not photo.extended.last_original_uploaded:
        return None
    with photo.extended.last_original_uploaded.open('rb') as f:
        return f.read()


def get_image_content(photo):
    if not photo.image:
        return None
    with photo.image.open('rb') as f:
        return f.read()


@override_settings(PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP=True)
class TestNewJpgThenSavesAndChanges(TestCase):
    """Test case 1: start with new JPG, then save, then various changes (same/diff content, webp, jpg)."""

    def test_1a_through_1j(self):
        # 1a. Imagen nueva JPG
        jpg1 = make_jpg_bytes('red')
        photo = Photo.objects.create(
            title='Test photo',
            slug='test-photo-jpg',
            image=SimpleUploadedFile('first.jpg', jpg1, 'image/jpeg'),
        )
        self.assertTrue(photo.image.name.endswith('.webp'), 'JPG should be converted to webp')
        self.assertIsNotNone(get_last_original_content(photo), 'last_original_uploaded should be set')
        self.assertEqual(get_last_original_content(photo), jpg1, 'last_original should store the jpg bytes')

        # 1b. Plain save (solo otro campo): no tocar last_original
        photo.title = 'Updated title'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, 'plain save => last_original unchanged')

        # 1c. Cambiarla por un JPG con distinto nombre pero mismo contenido
        photo.image.save('other_name.jpg', ContentFile(jpg1), save=True)
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, '1c: same content => last_original unchanged')

        # 1d. Plain save: no tocar last_original
        photo.title = 'Again'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, 'plain save => last_original unchanged')

        # 1e. Cambiarla por un JPG con distinto nombre y contenido
        jpg2 = make_jpg_bytes('green')
        photo.image.save('second.jpg', ContentFile(jpg2), save=True)
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg2, '1e: new content => last_original is jpg2')

        # 1f. Plain save: no tocar last_original
        photo.title = 'Green'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg2, 'plain save => last_original unchanged')

        # 1g. Cambiarla por un webp
        webp1 = make_webp_bytes('blue')
        photo.image.save('as_webp.webp', ContentFile(webp1), save=True)
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1, '1g: uploaded webp => last_original is webp1')

        # 1h. Plain save: no tocar last_original
        photo.title = 'Webp'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1, 'plain save => last_original unchanged')

        # 1i. Cambiarla por un JPG con distinto nombre y contenido (1º y 2º)
        jpg3 = make_jpg_bytes('yellow', size=(12, 12))
        photo.image.save('third.jpg', ContentFile(jpg3), save=True)
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg3, '1i: new jpg => last_original is jpg3')

        # 1j. Plain save: no tocar last_original
        photo.title = 'Yellow'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg3, 'plain save => last_original unchanged')


@override_settings(PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP=True)
class TestNewWebpThenSavesAndChanges(TestCase):
    """Test case 2: start with new WebP, then save, then various changes (webp/jpg analogous to case 1)."""

    def test_2a_through_2j(self):
        # 2a. Imagen nueva WebP
        webp1 = make_webp_bytes('blue')
        photo = Photo.objects.create(
            title='Test photo webp',
            slug='test-photo-webp',
            image=SimpleUploadedFile('first.webp', webp1, 'image/webp'),
        )
        self.assertTrue(photo.image.name.endswith('.webp'), 'already webp stays webp')
        self.assertIsNotNone(get_last_original_content(photo))
        self.assertEqual(get_last_original_content(photo), webp1, 'last_original stores the uploaded webp')

        # 2b. Plain save: no tocar last_original
        photo.title = 'Updated'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1)

        # 2c. Cambiarla por un webp con distinto nombre pero mismo contenido
        photo.image.save('other.webp', ContentFile(webp1), save=True)
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1, '2c: same content => last_original unchanged')

        # 2d. Plain save: no tocar last_original
        photo.title = 'Again'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1, 'plain save => last_original unchanged')

        # 2e. Cambiarla por un webp con distinto nombre y contenido
        webp2 = make_webp_bytes('green')
        photo.image.save('second.webp', ContentFile(webp2), save=True)
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp2, '2e: new content => last_original is webp2')

        # 2f. Plain save: no tocar last_original
        photo.title = 'Green'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp2, 'plain save => last_original unchanged')

        # 2g. Cambiarla por un jpg
        jpg1 = make_jpg_bytes('red')
        photo.image.save('as_jpg.jpg', ContentFile(jpg1), save=True)
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, '2g: jpg uploaded => converted, last_original is jpg1')

        # 2h. Plain save: no tocar last_original (ya convertido en 2g)
        photo.title = 'Jpg'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, 'plain save => last_original unchanged')

        # 2i. Cambiarla por un webp con distinto nombre y contenido (1º y 2º)
        webp3 = make_webp_bytes('yellow', size=(12, 12))
        photo.image.save('third.webp', ContentFile(webp3), save=True)
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp3, '2i: new webp => last_original is webp3')

        # 2j. Plain save: no tocar last_original
        photo.title = 'Yellow'
        photo.save()
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp3, 'plain save => last_original unchanged')


@override_settings(PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP=True)
class TestNewJpgViaAdmin(TestCase):
    """Same as TestNewJpgThenSavesAndChanges but via Django admin (test client). Only 1a for now."""

    def test_1a_via_admin(self):
        # 1a via admin: add a new Photo with JPG; expect webp + last_original set
        User = get_user_model()
        email = 'admin@%s' % settings.CORE_TEST_EMAIL_KNOWN_GOOD_DOMAIN
        user = User.objects.create_superuser('admin', email, 'password')
        client = Client()
        client.force_login(user)

        add_url = reverse('admin:photologue_photo_add')
        response = client.get(add_url)
        self.assertEqual(response.status_code, 200, 'GET add form should succeed')

        # Parse CSRF and formset prefix from the add form
        content = response.content.decode()
        csrf_match = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', content)
        self.assertTrue(csrf_match, 'Add form should contain csrfmiddlewaretoken')
        csrf_token = csrf_match.group(1)

        prefix_match = re.search(r'name="([^"]+)-TOTAL_FORMS"', content)
        self.assertTrue(prefix_match, 'Add form should contain inline formset TOTAL_FORMS')
        formset_prefix = prefix_match.group(1)

        # Get TOTAL_FORMS value from the page so we send the same
        total_forms_match = re.search(
            r'name="' + re.escape(formset_prefix) + r'-TOTAL_FORMS"\s+value="(\d+)"', content
        )
        total_forms = int(total_forms_match.group(1)) if total_forms_match else 1
        initial_forms_match = re.search(
            r'name="' + re.escape(formset_prefix) + r'-INITIAL_FORMS"\s+value="(\d+)"', content
        )
        initial_forms = int(initial_forms_match.group(1)) if initial_forms_match else 0
        min_num_match = re.search(
            r'name="' + re.escape(formset_prefix) + r'-MIN_NUM_FORMS"\s+value="(\d+)"', content
        )
        min_num = int(min_num_match.group(1)) if min_num_match else 0
        max_num_match = re.search(
            r'name="' + re.escape(formset_prefix) + r'-MAX_NUM_FORMS"\s+value="(\d+)"', content
        )
        max_num = int(max_num_match.group(1)) if max_num_match else 1000

        jpg1 = make_jpg_bytes('red')
        image_file = SimpleUploadedFile('first.jpg', jpg1, 'image/jpeg')

        post_data = {
            'csrfmiddlewaretoken': csrf_token,
            'title': 'Test photo admin',
            'slug': 'test-photo-admin-jpg',
            'caption': '',
            'crop_from': 'top',
            'is_public': 'on',
            # Inline formset management
            f'{formset_prefix}-TOTAL_FORMS': str(total_forms),
            f'{formset_prefix}-INITIAL_FORMS': str(initial_forms),
            f'{formset_prefix}-MIN_NUM_FORMS': str(min_num),
            f'{formset_prefix}-MAX_NUM_FORMS': str(max_num),
        }
        for i in range(total_forms):
            post_data[f'{formset_prefix}-{i}-date_taken'] = ''
            post_data[f'{formset_prefix}-{i}-type'] = 'f'
            post_data[f'{formset_prefix}-{i}-photographer'] = ''
            post_data[f'{formset_prefix}-{i}-agency'] = ''
            post_data[f'{formset_prefix}-{i}-focuspoint_x'] = '0'
            post_data[f'{formset_prefix}-{i}-focuspoint_y'] = '0'
            post_data[f'{formset_prefix}-{i}-radius_length'] = ''

        post_data['image'] = image_file
        response = client.post(add_url, data=post_data, format='multipart', follow=False)
        self.assertIn(
            response.status_code, (302, 303),
            'POST add should redirect on success; got %s. Content (first 1500 chars): %s'
            % (response.status_code, (response.content.decode() if response.content else '')[:1500])
        )

        photo = Photo.objects.get(slug='test-photo-admin-jpg')
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'), 'JPG should be converted to webp')
        self.assertIsNotNone(get_last_original_content(photo), 'last_original_uploaded should be set')
        self.assertEqual(get_last_original_content(photo), jpg1, 'last_original should store the jpg bytes')
