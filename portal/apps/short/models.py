# -*- coding: UTF-8 -*-
from __future__ import unicode_literals

from django.db.models import Model, URLField


class Url(Model):
    url = URLField()

    def __str__(self):
        return self.url

    def surl(self):
        return '<a href="/short/U/%i/">sURL</a>' % self.id

    surl.allow_tags = True

    def get_absolute_url(self):
        return "/short/url/%i/" % self.id
