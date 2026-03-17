import hashlib
import logging
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile

from photologue.models import get_storage_path

logger = logging.getLogger(__name__)


AUTO_CONVERT_TO_WEBP = getattr(settings, 'PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP', True)


def get_exif_data(image):
    try:
        exif_data = image._getexif()
        if exif_data is not None:
            return {
                TAGS.get(tag): value
                for tag, value in exif_data.items()
                if tag in TAGS
            }
    except AttributeError:
        # Handle cases where EXIF data is not available
        pass
    return {}


def _last_original_has_same_content(ext, content):
    """True if last_original_uploaded exists and its file content equals content (bytes)."""
    if not ext.last_original_uploaded:
        return False
    try:
        with ext.last_original_uploaded.open('rb') as f:
            return f.read() == content
    except (IOError, OSError):
        return False


def _save_last_original_file(ext, original_filename, content):
    """
    Save content to ext.last_original_uploaded. We always write via storage.save()
    and set the field name manually so Django's FileField never runs delete()
    with an empty previous name (ValueError: "The name must be given to delete().").
    Returns '' so callers use update() to persist (no model save → no delete).
    """
    path = get_storage_path(ext, original_filename)
    storage = ext.last_original_uploaded.storage
    saved_name = storage.save(path, ContentFile(content))
    ext.last_original_uploaded = saved_name
    return ''


def _persist_last_original_uploaded(ext, old_lor_name):
    """
    Persist ext.last_original_uploaded to DB. We always use update() to avoid
    Django's FileField save() calling storage.delete() with an empty or stale
    previous name (ValueError: "The name must be given to delete().").
    """
    ext.__class__.objects.filter(pk=ext.pk).update(
        last_original_uploaded=ext.last_original_uploaded.name
    )


def _content_is_webp(content):
    """True if bytes look like WebP (magic bytes)."""
    return len(content) >= 12 and content[:4] == b'RIFF' and content[8:12] == b'WEBP'


def convert_photo_image_to_webp(photo, save_last_original=True):
    """
    Convert the photo's image to WebP if it is not already WebP (detected by format, not extension).
    When save_last_original=True (e.g. auto-convert on save), saves a copy to last_original_uploaded.
    Deletes the original file after successful conversion (same behavior as default save).
    Returns True if conversion was performed, False if skipped (already WebP or error).
    """
    try:
        with photo.image.open('rb') as f:
            content = f.read()
        with Image.open(BytesIO(content)) as img:
            if getattr(img, 'format', None) == 'WEBP':
                # Already WebP: only sync last_original when the image was actually replaced
                # (pre_save stored _previous_image_name). Plain save (e.g. only caption changed)
                # must not touch files. Re-entry right after JPG->WebP is skipped via flag.
                if getattr(photo, '_webp_just_converted', False):
                    photo._webp_just_converted = False
                    return False
                previous_name = getattr(photo, '_previous_image_name', None)
                image_replaced = previous_name is None or photo.image.name != previous_name
                if not image_replaced and getattr(photo, '_previous_image_hash', None) is not None:
                    # Same path: check if content changed (e.g. admin re-upload same filename)
                    current_hash = hashlib.md5(content).hexdigest()
                    if current_hash != photo._previous_image_hash:
                        image_replaced = True
                if not image_replaced and getattr(photo, '_previous_image_hash', None) is None and hasattr(photo, 'extended'):
                    # No hash (e.g. read failed in pre_save): if both current and last_original are WebP
                    # and differ, treat as re-uploaded WebP (sync). Avoid when last_original is JPG (plain save).
                    ext = photo.extended
                    if ext.last_original_uploaded and _content_is_webp(content):
                        try:
                            with ext.last_original_uploaded.open('rb') as f:
                                last_content = f.read()
                            if _content_is_webp(last_content) and last_content != content:
                                image_replaced = True
                        except (IOError, OSError):
                            pass
                if save_last_original and hasattr(photo, 'extended') and image_replaced:
                    ext = photo.extended
                    if not _last_original_has_same_content(ext, content):
                        original_filename = Path(photo.image.name).name
                        old_lor_name = _save_last_original_file(ext, original_filename, content)
                        if ext.pk is not None:
                            _persist_last_original_uploaded(ext, old_lor_name)
                return False

            icc_profile = img.info.get("icc_profile")
            output = BytesIO()
            img.convert("RGB").save(output, format="WEBP", quality=90, icc_profile=icc_profile)

        old_name = photo.image.name
        original_path = Path(old_name)
        original_filename = original_path.name
        webp_name = original_path.stem + ".webp"

        # Save copy as last_original_uploaded (skip if content is already the same)
        if save_last_original and hasattr(photo, 'extended'):
            ext = photo.extended
            if not _last_original_has_same_content(ext, content):
                old_lor_name = _save_last_original_file(ext, original_filename, content)
                # Only update in DB if instance already has pk (e.g. model save).
                # When pk is None we're in the middle of an insert (e.g. admin inline);
                # the ongoing save will persist last_original_uploaded.
                if ext.pk is not None:
                    _persist_last_original_uploaded(ext, old_lor_name)

        photo.image.save(webp_name, ContentFile(output.getvalue()), save=False)
        photo._webp_just_converted = True  # so re-entry in "already WebP" branch won't overwrite last_original
        # Photologue's Photo.save() deletes _old_image; avoid storage.delete('') when name is empty
        old_image_name = getattr(getattr(photo, '_old_image', None), 'name', None) or ''
        if old_image_name:
            photo.save(update_fields=['image'])
        else:
            photo.__class__.objects.filter(pk=photo.pk).update(image=photo.image.name)

        # Delete the old file (default save behavior when replacing)
        if old_name and old_name != photo.image.name:
            storage = photo.image.storage
            if storage.exists(old_name):
                try:
                    storage.delete(old_name)
                except Exception as e:
                    logger.warning("Could not delete old file %s: %s", old_name, e)
        return True
    except Exception as e:
        logger.error("Failed to convert image %s to WebP: %s", photo.image.name, e)
        return False


def convert_to_webp(photo):
    """Convert photo to WebP on save if PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP is enabled."""
    if not AUTO_CONVERT_TO_WEBP:
        return
    convert_photo_image_to_webp(photo)
