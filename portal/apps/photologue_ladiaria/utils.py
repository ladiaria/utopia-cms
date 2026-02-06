from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from io import BytesIO
from django.core.files.base import ContentFile


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

    # Backup the original image when the photo is saved as webp
    photo.extended.original_image.save(original_filename, photo.image.file, save=False)

    # Open the image file (works both with local and remote storage backends)
    img = Image.open(photo.image)

    # TODO: Check if this is needed since WEBP does not contain EXIF data and I'm not sure if when saving
    # a picture in a regular format the EXIF data is populated in the date_taken field.
    # exif_data = get_exif_data(img)
    # date_taken = exif_data.get('DateTimeOriginal', None)
    # if date_taken:
    #     photo.date_taken = date_taken
    #     photo.save(fields=['date_taken'])

    # Get the ICC profile from the original image to avoid different colors in the webp
    icc_profile = img.info.get("icc_profile")

    # Prepare for saving to WebP with RGB conversion
    output = BytesIO()
    img = img.convert("RGB")  # Convert to RGB if not already
    img.save(output, format="WEBP", quality=90, icc_profile=icc_profile)  # Save as WebP with quality 90

    # Define the correct path without modifying image.name directly
    webp_name = original_path.stem + ".webp"  # Keep just the filename with .webp extension

    # Save the new image using the correct path
    photo.image.save(webp_name, ContentFile(output.getvalue()), save=False)
