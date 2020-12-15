from django.db import IntegrityError
from tagging.models import Tag

# capitalize all tags names

tags = Tag.objects.all()
for tag in tags:
    name = tag.name
    if name and len(name) >= 2:
        first = name[0]
        if 'a' <= first and first <= 'z':
            tag.name = tag.name.capitalize()
            try:
                tag.save()
            except IntegrityError:
                print('posible duplication with Tag %d %s' %
                      (tag.id, tag.name))
