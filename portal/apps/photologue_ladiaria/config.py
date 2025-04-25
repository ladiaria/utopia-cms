from os.path import join
import unicodedata
from django.utils.encoding import force_str

from photologue.apps import PhotologueConfig


def build_relative_path(dt, filename):
    return join("photologue/photos", dt.strftime('%Y-%m'), filename)


def get_image_path(instance, filename):
    fn = unicodedata.normalize('NFKD', force_str(filename)).encode('ascii', 'ignore').decode('ascii')
    return build_relative_path(instance.date_added, fn)


class PhotologueUtopiaConfig(PhotologueConfig):
    pass
