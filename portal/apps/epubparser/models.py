from __future__ import unicode_literals
from django.db import models
from django.db.models import CASCADE
from django.db.models import ForeignKey
from core.models import Section


# TODO: explain or remove this commented class
# class Section_test(models.Model):
#    description = models.CharField(max_length=150, choices=SECTIONS_AVAILABLE, default='1')

#    def __str__(self):
#        return self.description


class EpubFile(models.Model):
    """ This holds a single user uploaded file """
    f = models.FileField(upload_to='epubparser/%Y/%m/%d')  # Date-based directories
    section = ForeignKey(Section, on_delete=CASCADE)

    def __str__(self):
        return self.f.url
