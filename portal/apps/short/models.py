# -*- coding: UTF-8 -*-
from __future__ import unicode_literals

from django.db.models import Model, URLField
from django.utils.safestring import mark_safe


class Url(Model):
    url = URLField()

    def __str__(self):
        return self.url

    def url_formatted(self):
        if len(self.url) > 150:
            return f"{str(self.url)[:150]}..."
        else:
            return f"{str(self.url)}"
    url_formatted.short_description = 'URL'

    def surl(self):
        return mark_safe('<a href="/short/U/%d/">sURL</a>' % self.id)

    def get_absolute_url(self):
        return "/short/url/%d/" % self.id
