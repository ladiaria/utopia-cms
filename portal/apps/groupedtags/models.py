# -*- coding: utf-8 -*-

from django.db.models import Model, SlugField, ManyToManyField

from tagging.models import Tag


class TagGroup(Model):
    slug = SlugField('slug', unique=True)
    tags = ManyToManyField(Tag, blank=True)

    def __str__(self):
        return self.slug

    def tags_names(self):
        return ', '.join(self.tags.values_list('name', flat=True))
