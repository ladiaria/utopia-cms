from os import unlink
from os.path import dirname, exists, splitext
from copy import deepcopy
from tqdm import tqdm

from django.utils.text import slugify

from photologue.models import Photo


def realocate(filter_kwargs={}):
    target_qs = Photo.objects.filter(**filter_kwargs) if filter_kwargs else Photo.objects
    moved, total = 0, target_qs.count()
    for photo in tqdm(target_qs.iterator(), total=total):
        try:
            if exists(photo.image.path) and dirname(str(photo.image)) == "photologue/photos":
                pc = deepcopy(photo)
                filename_splitted = splitext(pc.image_filename())
                pc.image.save(slugify(filename_splitted[0]) + filename_splitted[1], pc.image.file)
                unlink(photo.image.path)
        except Exception as e:
            print(e)
        else:
            moved += 1

    print(f"Moved {moved} of {total}")


def non_existent_photos():
    for p in Photo.objects.iterator():
        pp = p.image.path
        if not exists(pp):
            yield p.id, pp
