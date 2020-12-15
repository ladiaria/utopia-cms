# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'YouTubeVideo', fields ['title']
        db.delete_unique('videologue_youtubevideo', ['title'])


        # Changing field 'YouTubeVideo.title'
        db.alter_column('videologue_youtubevideo', 'title', self.gf('django.db.models.fields.CharField')(max_length=50, null=True))

        # Changing field 'YouTubeVideo.description'
        db.alter_column('videologue_youtubevideo', 'description', self.gf('django.db.models.fields.TextField')(null=True))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'YouTubeVideo.title'
        raise RuntimeError("Cannot reverse this migration. 'YouTubeVideo.title' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'YouTubeVideo.title'
        db.alter_column('videologue_youtubevideo', 'title', self.gf('django.db.models.fields.CharField')(max_length=50, unique=True))
        # Adding unique constraint on 'YouTubeVideo', fields ['title']
        db.create_unique('videologue_youtubevideo', ['title'])


        # User chose to not deal with backwards NULL issues for 'YouTubeVideo.description'
        raise RuntimeError("Cannot reverse this migration. 'YouTubeVideo.description' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'YouTubeVideo.description'
        db.alter_column('videologue_youtubevideo', 'description', self.gf('django.db.models.fields.TextField')())

    models = {
        'videologue.video': {
            'Meta': {'object_name': 'Video'},
            'byline': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_uploaded': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'times_viewed': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'videologue.youtubevideo': {
            'Meta': {'object_name': 'YouTubeVideo'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'})
        }
    }

    complete_apps = ['videologue']