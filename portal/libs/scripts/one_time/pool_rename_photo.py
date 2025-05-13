from os import unlink
from os.path import dirname
from copy import deepcopy

from tqdm import tqdm

from photologue.models import Photo


def realocate(filter_kwargs={}):
    target_qs = Photo.objects.filter(**filter_kwargs) if filter_kwargs else Photo.objects
    moved, total = 0, target_qs.count()
    for photo in tqdm(target_qs.iterator(), total=total):
        try:
            if dirname(str(photo.image)) == "photologue/photos":
                pc = deepcopy(photo)
                pc.image.save(pc.image_filename(), pc.image.file)
                unlink(photo.image.path)
        except Exception as e:
            print(e)
        else:
            moved += 1

    print(f"Moved {moved} of {total}")
