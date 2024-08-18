import os
from django.conf import settings
from core.models import Edition


relpath = None

for e in Edition.objects.iterator():
    save_edition, supplements_saved = False, False

    for attr in ('pdf', 'cover'):
        obj = getattr(e, attr)
        if obj:
            relpath, filename = os.path.split(obj.name)
            if e.publication.slug not in relpath:
                if os.path.exists(obj.path):
                    new_relpath = relpath.replace(
                        'editions/', 'editions/%s/' % e.publication.slug)
                    # mkdir only once
                    try:
                        os.mkdir(
                            os.path.join(settings.MEDIA_ROOT, new_relpath))
                    except OSError:
                        pass
                    # move pdf
                    os.rename(
                        obj.path, obj.path.replace(
                            '/editions/',
                            '/editions/%s/' % e.publication.slug))
                    setattr(e, attr, os.path.join(new_relpath, filename))
                else:
                    # file does not exist, clear attribute
                    setattr(e, attr, None)
                save_edition = True

    for s in e.supplements.all():
        save_supplement = False
        for attr in ('pdf', 'cover'):
            obj = getattr(s, attr)
            if obj:
                relpath, filename = os.path.split(obj.name)
                if e.publication.slug not in relpath:
                    if os.path.exists(obj.path):
                        new_relpath = relpath.replace(
                            'editions/', 'editions/%s/' % e.publication.slug)
                        # mkdir only once
                        try:
                            os.mkdir(
                                os.path.join(settings.MEDIA_ROOT, new_relpath))
                        except OSError:
                            pass
                        # move pdf
                        os.rename(
                            obj.path, obj.path.replace(
                                '/editions/',
                                '/editions/%s/' % e.publication.slug))
                        setattr(s, attr, os.path.join(new_relpath, filename))
                    else:
                        # file does not exist, clear attribute
                        setattr(s, attr, None)
                    save_supplement = True
        if save_supplement:
            s.save()
            supplements_saved = True

    if save_edition or supplements_saved:
        if save_edition:
            e.save()
        try:
            os.rmdir(os.path.join(settings.MEDIA_ROOT, relpath))
        except OSError:
            pass
