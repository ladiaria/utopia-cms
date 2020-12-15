# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LiveEmbedEvent'
        db.create_table('cartelera_liveembedevent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('access_type', self.gf('django.db.models.fields.CharField')(default='s', max_length=1)),
            ('in_home', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('notification', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('notification_text', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('notification_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('cartelera', ['LiveEmbedEvent'])


    def backwards(self, orm):
        # Deleting model 'LiveEmbedEvent'
        db.delete_table('cartelera_liveembedevent')


    models = {
        'actstream.action': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'cartelera.categoriaevento': {
            'Meta': {'object_name': 'CategoriaEvento'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nombre': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        'cartelera.cine': {
            'Meta': {'object_name': 'Cine'},
            'address': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nombre': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'phones': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        'cartelera.evento': {
            'Meta': {'object_name': 'Evento', '_ormbases': ['cartelera.EventoBase']},
            'eventobase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cartelera.EventoBase']", 'unique': 'True', 'primary_key': 'True'})
        },
        'cartelera.eventobase': {
            'Meta': {'object_name': 'EventoBase'},
            'categoria': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cartelera.CategoriaEvento']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'poster': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'precio': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'rating_score': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'rating_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        },
        'cartelera.liveembedevent': {
            'Meta': {'object_name': 'LiveEmbedEvent'},
            'access_type': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_home': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'notification': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'notification_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notification_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'cartelera.obraenteatro': {
            'Meta': {'object_name': 'ObraEnTeatro'},
            'horarios': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'obra': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'horarios'", 'to': "orm['cartelera.ObraTeatro']"}),
            'teatro': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'horarios'", 'to': "orm['cartelera.Teatro']"})
        },
        'cartelera.obrateatro': {
            'Meta': {'object_name': 'ObraTeatro', '_ormbases': ['cartelera.EventoBase']},
            'eventobase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cartelera.EventoBase']", 'unique': 'True', 'primary_key': 'True'})
        },
        'cartelera.pelicula': {
            'Meta': {'object_name': 'Pelicula', '_ormbases': ['cartelera.EventoBase']},
            'eventobase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cartelera.EventoBase']", 'unique': 'True', 'primary_key': 'True'})
        },
        'cartelera.peliculaencine': {
            'Meta': {'object_name': 'PeliculaEnCine'},
            'cine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'horarios'", 'to': "orm['cartelera.Cine']"}),
            'horarios': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pelicula': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'horarios'", 'to': "orm['cartelera.Pelicula']"})
        },
        'cartelera.teatro': {
            'Meta': {'object_name': 'Teatro'},
            'address': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nombre': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'phones': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['cartelera']