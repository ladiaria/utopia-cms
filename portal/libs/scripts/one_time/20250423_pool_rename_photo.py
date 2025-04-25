from os import unlink
from os.path import dirname
from copy import deepcopy

from tqdm import tqdm

from photologue.models import Photo


def realocate():
    moved, total = 0, Photo.objects.count()
    for photo in tqdm(Photo.objects.iterator(), total=total):
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
