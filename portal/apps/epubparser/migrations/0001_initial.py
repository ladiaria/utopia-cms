# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'EpubFile'
        db.create_table('epubparser_epubfile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('f', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('section', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Section'])),
        ))
        db.send_create_signal('epubparser', ['EpubFile'])


    def backwards(self, orm):
        # Deleting model 'EpubFile'
        db.delete_table('epubparser_epubfile')


    models = {
        'core.section': {
            'Meta': {'ordering': "('name', 'date_created')", 'object_name': 'Section'},
            'contact': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'home_order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_home': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        'epubparser.epubfile': {
            'Meta': {'object_name': 'EpubFile'},
            'f': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'section': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Section']"})
        }
    }

    complete_apps = ['epubparser']