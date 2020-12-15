# -*- coding: UTF-8 -*-
from django.db.models import *


class Url(Model):
    url = URLField()

    def __unicode__(self):
        return self.url

    def surl(self):
        return '<a href="/short/U/%i/">sURL</a>' % self.id

    surl.allow_tags = True

    def get_absolute_url(self):
        return "/short/url/%i/" % self.id
