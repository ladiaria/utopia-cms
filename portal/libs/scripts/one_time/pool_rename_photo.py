from os import unlink
from os.path import dirname, exists, splitext
from copy import deepcopy
from tqdm import tqdm

from django.utils.text import slugify

from photologue.models import Photo


def realocate(filter_kwargs={}, verbose=False, dry_run=False, ignore_errors=False):
    target_qs = Photo.objects.filter(**filter_kwargs) if filter_kwargs else Photo.objects
    non_existent, errors, in_pool, moved, total = 0, 0, 0, 0, target_qs.count()
    for photo in tqdm(target_qs.iterator(), total=total):
        try:
            if exists(photo.image.path):
                if dirname(str(photo.image)) == "photologue/photos":
                    if dry_run:
                        if verbose:
                            print(f"Would move {photo.image.path} to pool")
                        moved += 1
                        continue
                    pc = deepcopy(photo)
                    filename_splitted = splitext(pc.image_filename())
                    pc.image.save(slugify(filename_splitted[0]) + filename_splitted[1], pc.image.file)
                    unlink(photo.image.path)
                    moved += 1
                else:
                    in_pool += 1
            else:
                non_existent += 1
        except Exception as e:
            errors += 1
            if verbose:
                print(e)
            if not ignore_errors:
                break

    m = "Would move" if dry_run else "Moved"
    print(f"{m} {moved} of {total} (Non-existent: {non_existent}, Errors: {errors}, Already in pool: {in_pool})")


def non_existent_photos():
    for p in Photo.objects.iterator():
        pp = p.image.storage.path(p.image.name)
        if not exists(pp):
            yield p.id, pp
