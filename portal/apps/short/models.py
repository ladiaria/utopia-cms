# -*- coding: UTF-8 -*-
from __future__ import unicode_literals

from django.db.models import Model, URLField
from django.utils.safestring import mark_safe


class Url(Model):
    url = URLField()

    def __str__(self):
        return self.url

    def surl(self):
        return mark_safe('<a href="/short/U/%i/">sURL</a>' % self.id)

    def get_absolute_url(self):
        return "/short/url/%i/" % self.id
