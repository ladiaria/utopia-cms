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
        self.assertEqual(get_last_original_content(photo), jpg1, '2g: jpg upload => converted, last_original is jpg1')

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


def _parse_admin_form(response):
    """
    Parse admin form HTML; return dict with csrf_token, formset_prefix, total_forms, initial_forms, min_num, max_num.
    """
    content = response.content.decode()
    csrf_match = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', content)
    assert csrf_match, 'Form should contain csrfmiddlewaretoken'
    prefix_match = re.search(r'name="([^"]+)-TOTAL_FORMS"', content)
    assert prefix_match, 'Form should contain inline formset TOTAL_FORMS'
    formset_prefix = prefix_match.group(1)
    total_forms, initial_forms, min_num, max_num = 1, 0, 0, 1000
    m = re.search(r'name="' + re.escape(formset_prefix) + r'-TOTAL_FORMS"\s+value="(\d+)"', content)
    if m:
        total_forms = int(m.group(1))
    m = re.search(r'name="' + re.escape(formset_prefix) + r'-INITIAL_FORMS"\s+value="(\d+)"', content)
    if m:
        initial_forms = int(m.group(1))
    m = re.search(r'name="' + re.escape(formset_prefix) + r'-MIN_NUM_FORMS"\s+value="(\d+)"', content)
    if m:
        min_num = int(m.group(1))
    m = re.search(r'name="' + re.escape(formset_prefix) + r'-MAX_NUM_FORMS"\s+value="(\d+)"', content)
    if m:
        max_num = int(m.group(1))
    return {
        'csrf_token': csrf_match.group(1),
        'formset_prefix': formset_prefix,
        'total_forms': total_forms,
        'initial_forms': initial_forms,
        'min_num': min_num,
        'max_num': max_num,
    }


def _build_change_post_data(photo, parsed, title=None, image_file=None):
    """Build POST data for admin photo change form. Override title and/or image_file if given."""
    ext = photo.extended
    date_taken = str(photo.date_taken) if photo.date_taken else ''
    p = parsed['formset_prefix']
    total = parsed['total_forms']
    post_data = {
        'csrfmiddlewaretoken': parsed['csrf_token'],
        'title': title if title is not None else photo.title,
        'slug': photo.slug,
        'caption': photo.caption or '',
        'crop_from': getattr(photo, 'crop_from', 'top') or 'top',
        'is_public': 'on' if photo.is_public else '',
        f'{p}-TOTAL_FORMS': str(total),
        f'{p}-INITIAL_FORMS': str(parsed['initial_forms']),
        f'{p}-MIN_NUM_FORMS': str(parsed['min_num']),
        f'{p}-MAX_NUM_FORMS': str(parsed['max_num']),
    }
    for i in range(total):
        post_data[f'{p}-{i}-date_taken'] = date_taken if i == 0 else ''
        post_data[f'{p}-{i}-type'] = 'f'
        post_data[f'{p}-{i}-photographer'] = str(ext.photographer_id) if ext.photographer_id else ''
        post_data[f'{p}-{i}-agency'] = str(ext.agency_id) if ext.agency_id else ''
        post_data[f'{p}-{i}-focuspoint_x'] = getattr(ext, 'focuspoint_x', '0') or '0'
        post_data[f'{p}-{i}-focuspoint_y'] = getattr(ext, 'focuspoint_y', '0') or '0'
        post_data[f'{p}-{i}-radius_length'] = str(ext.radius_length) if ext.radius_length is not None else ''
        if i == 0 and ext.pk:
            post_data[f'{p}-{i}-id'] = str(ext.pk)
    if image_file is not None:
        post_data['image'] = image_file
    return post_data


class ViaAdminBase(TestCase):
    add_url = reverse('admin:photologue_photo_add')

    def setUp(self):
        User = get_user_model()
        email = 'admin@%s' % settings.CORE_TEST_EMAIL_KNOWN_GOOD_DOMAIN
        user = User.objects.create_superuser('admin', email, 'password')
        self.client = Client()
        self.client.force_login(user)


@override_settings(PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP=True)
class TestNewJpgViaAdmin(ViaAdminBase):
    """Same as TestNewJpgThenSavesAndChanges but via Django admin (test client). Covers 1a through 1j."""

    def test_1a_through_1j_via_admin(self):
        client = self.client
        response = client.get(self.add_url)
        self.assertEqual(response.status_code, 200, 'GET add form should succeed')
        parsed = _parse_admin_form(response)
        p = parsed['formset_prefix']
        total = parsed['total_forms']

        jpg1 = make_jpg_bytes('red')
        post_data = {
            'csrfmiddlewaretoken': parsed['csrf_token'],
            'title': 'Test photo admin',
            'slug': 'test-photo-admin-jpg',
            'caption': '',
            'crop_from': 'top',
            'is_public': 'on',
            f'{p}-TOTAL_FORMS': str(total),
            f'{p}-INITIAL_FORMS': str(parsed['initial_forms']),
            f'{p}-MIN_NUM_FORMS': str(parsed['min_num']),
            f'{p}-MAX_NUM_FORMS': str(parsed['max_num']),
        }
        for i in range(total):
            post_data[f'{p}-{i}-date_taken'] = ''
            post_data[f'{p}-{i}-type'] = 'f'
            post_data[f'{p}-{i}-photographer'] = ''
            post_data[f'{p}-{i}-agency'] = ''
            post_data[f'{p}-{i}-focuspoint_x'] = '0'
            post_data[f'{p}-{i}-focuspoint_y'] = '0'
            post_data[f'{p}-{i}-radius_length'] = ''

        post_data['image'] = SimpleUploadedFile('first.jpg', jpg1, 'image/jpeg')
        response = client.post(self.add_url, data=post_data, format='multipart', follow=False)
        self.assertIn(
            response.status_code, (302, 303),
            'POST add should redirect; got %s: %s'
            % (response.status_code, (response.content.decode() if response.content else '')[:1500])
        )

        photo = Photo.objects.get(slug='test-photo-admin-jpg')
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'), '1a: JPG should be converted to webp')
        self.assertIsNotNone(get_last_original_content(photo), '1a: last_original_uploaded should be set')
        self.assertEqual(get_last_original_content(photo), jpg1, '1a: last_original should store the jpg bytes')

        change_url = reverse('admin:photologue_photo_change', args=[photo.pk])

        # 1b. Plain save (solo otro campo): no tocar last_original
        response = client.get(change_url)
        self.assertEqual(response.status_code, 200)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Updated title')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(
            response.status_code,
            (302, 303),
            '1b POST: %s' % (response.content.decode()[:500] if response.content else '')
        )
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, '1b: plain save => last_original unchanged')

        # 1c. Cambiarla por un JPG con distinto nombre pero mismo contenido
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(
            photo, parsed,
            image_file=SimpleUploadedFile('other_name.jpg', jpg1, 'image/jpeg'),
        )
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, '1c: same content => last_original unchanged')

        # 1d. Plain save: no tocar last_original
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Again')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, '1d: plain save => last_original unchanged')

        # 1e. Cambiarla por un JPG con distinto nombre y contenido
        jpg2 = make_jpg_bytes('green')
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(
            photo, parsed,
            image_file=SimpleUploadedFile('second.jpg', jpg2, 'image/jpeg'),
        )
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg2, '1e: new content => last_original is jpg2')

        # 1f. Plain save: no tocar last_original
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Green')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg2, '1f: plain save => last_original unchanged')

        # 1g. Cambiarla por un webp
        webp1 = make_webp_bytes('blue')
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(
            photo, parsed,
            image_file=SimpleUploadedFile('as_webp.webp', webp1, 'image/webp'),
        )
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1, '1g: uploaded webp => last_original is webp1')

        # 1h. Plain save: no tocar last_original
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Webp')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1, '1h: plain save => last_original unchanged')

        # 1i. Cambiarla por un JPG con distinto nombre y contenido
        jpg3 = make_jpg_bytes('yellow', size=(12, 12))
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(
            photo, parsed,
            image_file=SimpleUploadedFile('third.jpg', jpg3, 'image/jpeg'),
        )
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg3, '1i: new jpg => last_original is jpg3')

        # 1j. Plain save: no tocar last_original
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Yellow')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg3, '1j: plain save => last_original unchanged')


@override_settings(PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP=True)
class TestNewWebpViaAdmin(ViaAdminBase):
    """Same as TestNewWebpThenSavesAndChanges but via Django admin (test client). Covers 2a through 2j."""

    def test_2a_through_2j_via_admin(self):
        client = self.client
        response = client.get(self.add_url)
        self.assertEqual(response.status_code, 200, 'GET add form should succeed')
        parsed = _parse_admin_form(response)
        p = parsed['formset_prefix']
        total = parsed['total_forms']

        # 2a. Imagen nueva WebP
        webp1 = make_webp_bytes('blue')
        post_data = {
            'csrfmiddlewaretoken': parsed['csrf_token'],
            'title': 'Test photo webp admin',
            'slug': 'test-photo-admin-webp',
            'caption': '',
            'crop_from': 'top',
            'is_public': 'on',
            f'{p}-TOTAL_FORMS': str(total),
            f'{p}-INITIAL_FORMS': str(parsed['initial_forms']),
            f'{p}-MIN_NUM_FORMS': str(parsed['min_num']),
            f'{p}-MAX_NUM_FORMS': str(parsed['max_num']),
        }
        for i in range(total):
            post_data[f'{p}-{i}-date_taken'] = ''
            post_data[f'{p}-{i}-type'] = 'f'
            post_data[f'{p}-{i}-photographer'] = ''
            post_data[f'{p}-{i}-agency'] = ''
            post_data[f'{p}-{i}-focuspoint_x'] = '0'
            post_data[f'{p}-{i}-focuspoint_y'] = '0'
            post_data[f'{p}-{i}-radius_length'] = ''

        post_data['image'] = SimpleUploadedFile('first.webp', webp1, 'image/webp')
        response = client.post(self.add_url, data=post_data, format='multipart', follow=False)
        self.assertIn(
            response.status_code, (302, 303),
            'POST add should redirect; got %s: %s'
            % (response.status_code, (response.content.decode() if response.content else '')[:1500])
        )

        photo = Photo.objects.get(slug='test-photo-admin-webp')
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'), '2a: already webp stays webp')
        self.assertIsNotNone(get_last_original_content(photo), '2a: last_original_uploaded should be set')
        self.assertEqual(get_last_original_content(photo), webp1, '2a: last_original stores the uploaded webp')

        change_url = reverse('admin:photologue_photo_change', args=[photo.pk])

        # 2b. Plain save: no tocar last_original
        response = client.get(change_url)
        self.assertEqual(response.status_code, 200)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Updated')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(
            response.status_code,
            (302, 303),
            '2b POST: %s' % (response.content.decode()[:500] if response.content else '')
        )
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1, '2b: plain save => last_original unchanged')

        # 2c. Cambiarla por un webp con distinto nombre pero mismo contenido
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(
            photo, parsed,
            image_file=SimpleUploadedFile('other.webp', webp1, 'image/webp'),
        )
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1, '2c: same content => last_original unchanged')

        # 2d. Plain save: no tocar last_original
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Again')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp1, '2d: plain save => last_original unchanged')

        # 2e. Cambiarla por un webp con distinto nombre y contenido
        webp2 = make_webp_bytes('green')
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(
            photo, parsed,
            image_file=SimpleUploadedFile('second.webp', webp2, 'image/webp'),
        )
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp2, '2e: new content => last_original is webp2')

        # 2f. Plain save: no tocar last_original
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Green')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp2, '2f: plain save => last_original unchanged')

        # 2g. Cambiarla por un jpg
        jpg1 = make_jpg_bytes('red')
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(
            photo, parsed,
            image_file=SimpleUploadedFile('as_jpg.jpg', jpg1, 'image/jpeg'),
        )
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, '2g: jpg upload => converted, last_original is jpg1')

        # 2h. Plain save: no tocar last_original
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Jpg')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), jpg1, '2h: plain save => last_original unchanged')

        # 2i. Cambiarla por un webp con distinto nombre y contenido
        webp3 = make_webp_bytes('yellow', size=(12, 12))
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(
            photo, parsed,
            image_file=SimpleUploadedFile('third.webp', webp3, 'image/webp'),
        )
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp3, '2i: new webp => last_original is webp3')

        # 2j. Plain save: no tocar last_original
        response = client.get(change_url)
        parsed = _parse_admin_form(response)
        post_data = _build_change_post_data(photo, parsed, title='Yellow')
        response = client.post(change_url, data=post_data, format='multipart', follow=False)
        self.assertIn(response.status_code, (302, 303))
        photo.refresh_from_db()
        photo.extended.refresh_from_db()
        self.assertTrue(photo.image.name.endswith('.webp'))
        self.assertEqual(get_last_original_content(photo), webp3, '2j: plain save => last_original unchanged')
