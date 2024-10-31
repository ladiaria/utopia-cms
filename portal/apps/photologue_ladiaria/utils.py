from pathlib import Path
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from photologue.models import Photo

def convert_to_webp(photo):

    if photo.image.name.endswith('.webp'):
        return

    # Open the image file (works both with local and remote storage backends)
    img = Image.open(photo.image)
    icc_profile = img.info.get("icc_profile")

    # Prepare for saving to WebP with RGB conversion
    output = BytesIO()
    img = img.convert("RGB")  # Convert to RGB if not already
    img.save(output, format="WEBP", quality=90, icc_profile=icc_profile)  # Save as WebP with quality 90

    # Define the correct path without modifying image.name directly
    original_path = Path(photo.image.name)
    webp_name = original_path.stem + ".webp"  # Keep just the filename with .webp extension

    # Save the new image using the correct path
    photo.image.save(webp_name, ContentFile(output.getvalue()), save=False)
