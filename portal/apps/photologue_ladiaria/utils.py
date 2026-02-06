import logging
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from io import BytesIO
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


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


def convert_to_webp(photo):

    if photo.image.name.endswith('.webp'):
        # The photo is already a webp, there's no need to convert it
        return

    original_path = Path(photo.image.name)
    original_filename = original_path.name

    try:
        # Backup the original image when the photo is saved as webp
        photo.extended.original_image.save(original_filename, photo.image.file, save=False)

        # Open the image file (works both with local and remote storage backends)
        with Image.open(photo.image) as img:
            # Get the ICC profile from the original image to avoid different colors in the webp
            icc_profile = img.info.get("icc_profile")

            # Prepare for saving to WebP with RGB conversion
            output = BytesIO()
            img.convert("RGB").save(output, format="WEBP", quality=90, icc_profile=icc_profile)

        # Define the correct path without modifying image.name directly
        webp_name = original_path.stem + ".webp"

        # Save the new image using the correct path
        photo.image.save(webp_name, ContentFile(output.getvalue()), save=False)

        # Persist changes to the database (the .webp check at the top prevents infinite loops)
        photo.save(update_fields=['image'])
        photo.extended.save(update_fields=['original_image'])
    except Exception as e:
        logger.error("Failed to convert image %s to WebP: %s", photo.image.name, e)
