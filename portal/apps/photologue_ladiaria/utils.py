import logging
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# When True, photos are automatically converted to WebP on save (default: False).
AUTO_CONVERT_TO_WEBP = getattr(
    settings, 'PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP', False
)


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


def convert_photo_image_to_webp(photo):
    """
    Convert the photo's image to WebP if it is not already WebP (detected by format, not extension).
    Deletes the original file after successful conversion (same behavior as default save).
    Returns True if conversion was performed, False if skipped (already WebP or error).
    """
    try:
        with Image.open(photo.image) as img:
            if getattr(img, 'format', None) == 'WEBP':
                return False

            icc_profile = img.info.get("icc_profile")
            output = BytesIO()
            img.convert("RGB").save(output, format="WEBP", quality=90, icc_profile=icc_profile)

        old_name = photo.image.name
        original_path = Path(old_name)
        webp_name = original_path.stem + ".webp"
        photo.image.save(webp_name, ContentFile(output.getvalue()), save=False)
        photo.save(update_fields=['image'])

        # Delete the old file (default save behavior when replacing)
        if old_name != photo.image.name:
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
