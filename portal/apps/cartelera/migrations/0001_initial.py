# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CategoriaEvento'
        db.create_table('cartelera_categoriaevento', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('nombre', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('order', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('cartelera', ['CategoriaEvento'])

        # Adding model 'EventoBase'
        db.create_table('cartelera_eventobase', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('categoria', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cartelera.CategoriaEvento'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('end', self.gf('django.db.models.fields.DateTimeField')()),
            ('precio', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('poster', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('rating_votes', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, blank=True)),
            ('rating_score', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
        ))
        db.send_create_signal('cartelera', ['EventoBase'])

        # Adding model 'Pelicula'
        db.create_table('cartelera_pelicula', (
            ('eventobase_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['cartelera.EventoBase'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('cartelera', ['Pelicula'])

        # Adding model 'ObraTeatro'
        db.create_table('cartelera_obrateatro', (
            ('eventobase_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['cartelera.EventoBase'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('cartelera', ['ObraTeatro'])

        # Adding model 'Cine'
        db.create_table('cartelera_cine', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('nombre', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('address', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('phones', self.gf('django.db.models.fields.CharField')(max_length=250)),
        ))
        db.send_create_signal('cartelera', ['Cine'])

        # Adding model 'Teatro'
        db.create_table('cartelera_teatro', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('nombre', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('address', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('phones', self.gf('django.db.models.fields.CharField')(max_length=250)),
        ))
        db.send_create_signal('cartelera', ['Teatro'])

        # Adding model 'Evento'
        db.create_table('cartelera_evento', (
            ('eventobase_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['cartelera.EventoBase'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('cartelera', ['Evento'])

        # Adding model 'PeliculaEnCine'
        db.create_table('cartelera_peliculaencine', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('horarios', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('pelicula', self.gf('django.db.models.fields.related.ForeignKey')(related_name='horarios', to=orm['cartelera.Pelicula'])),
            ('cine', self.gf('django.db.models.fields.related.ForeignKey')(related_name='horarios', to=orm['cartelera.Cine'])),
        ))
        db.send_create_signal('cartelera', ['PeliculaEnCine'])

        # Adding model 'ObraEnTeatro'
        db.create_table('cartelera_obraenteatro', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('horarios', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('obra', self.gf('django.db.models.fields.related.ForeignKey')(related_name='horarios', to=orm['cartelera.ObraTeatro'])),
            ('teatro', self.gf('django.db.models.fields.related.ForeignKey')(related_name='horarios', to=orm['cartelera.Teatro'])),
        ))
        db.send_create_signal('cartelera', ['ObraEnTeatro'])


    def backwards(self, orm):
        # Deleting model 'CategoriaEvento'
        db.delete_table('cartelera_categoriaevento')

        # Deleting model 'EventoBase'
        db.delete_table('cartelera_eventobase')

        # Deleting model 'Pelicula'
        db.delete_table('cartelera_pelicula')

        # Deleting model 'ObraTeatro'
        db.delete_table('cartelera_obrateatro')

        # Deleting model 'Cine'
        db.delete_table('cartelera_cine')

        # Deleting model 'Teatro'
        db.delete_table('cartelera_teatro')

        # Deleting model 'Evento'
        db.delete_table('cartelera_evento')

        # Deleting model 'PeliculaEnCine'
        db.delete_table('cartelera_peliculaencine')

        # Deleting model 'ObraEnTeatro'
        db.delete_table('cartelera_obraenteatro')


    models = {
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
        }
    }

    complete_apps = ['cartelera']