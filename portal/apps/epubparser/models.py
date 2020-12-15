from django.db import models
from django.db.models import ForeignKey
from core.models import Section



#class Section_test(models.Model):
#    description = models.CharField(max_length=150,
#                                   choices=SECTIONS_AVAILABLE, default='1')

#    def __unicode__(self):
#        return self.description


class EpubFile(models.Model):
    """This holds a single user uploaded file"""
    f = models.FileField(upload_to='epubparser/%Y/%m/%d')  # Date-based directories
    section = ForeignKey(Section)

    def __unicode__(self):
        return self.f.url

