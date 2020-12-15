# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'NewsletterDelivery'
        db.create_table(u'dashboard_newsletterdelivery', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('delivery_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, blank=True)),
            ('newsletter_name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('user_sent', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('subscriber_sent', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('user_refused', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('subscriber_refused', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('user_opened', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('subscriber_opened', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('user_bounces', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('subscriber_bounces', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'dashboard', ['NewsletterDelivery'])

        # Adding unique constraint on 'NewsletterDelivery', fields ['delivery_date', 'newsletter_name']
        db.create_unique(u'dashboard_newsletterdelivery', ['delivery_date', 'newsletter_name'])


    def backwards(self, orm):
        # Removing unique constraint on 'NewsletterDelivery', fields ['delivery_date', 'newsletter_name']
        db.delete_unique(u'dashboard_newsletterdelivery', ['delivery_date', 'newsletter_name'])

        # Deleting model 'NewsletterDelivery'
        db.delete_table(u'dashboard_newsletterdelivery')


    models = {
        u'dashboard.newsletterdelivery': {
            'Meta': {'unique_together': "(('delivery_date', 'newsletter_name'),)", 'object_name': 'NewsletterDelivery'},
            'delivery_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'newsletter_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'subscriber_bounces': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscriber_opened': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscriber_refused': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscriber_sent': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user_bounces': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user_opened': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user_refused': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user_sent': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dashboard']