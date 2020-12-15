# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'SubscriptionPrices'
        db.create_table(u'thedaily_subscriptionprices', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subscription_type', self.gf('django.db.models.fields.CharField')(default='PAPYDIM', unique=True, max_length=7)),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('order', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True)),
            ('paypal_button_id', self.gf('django.db.models.fields.CharField')(max_length=13, null=True, blank=True)),
            ('auth_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.Group'], null=True, blank=True)),
            ('publication', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Publication'], null=True, blank=True)),
            ('ga_sku', self.gf('django.db.models.fields.CharField')(max_length=10, null=True, blank=True)),
            ('ga_name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('ga_category', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
        ))
        db.send_create_signal(u'thedaily', ['SubscriptionPrices'])

        # Adding model 'Subscriber'
        db.create_table(u'thedaily_subscriber', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('costumer_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True, null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='subscriber', unique=True, null=True, to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('province', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('profile_photo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('document', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('downloads', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, null=True, blank=True)),
            ('pdf', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('lento_pdf', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('ruta', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('plan_id', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('ruta_lento', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('ruta_fs', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('days', self.gf('django.db.models.fields.CharField')(default=None, max_length=5, null=True)),
            ('allow_promotions', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('allow_polls', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('subscription_mode', self.gf('django.db.models.fields.CharField')(default=None, max_length=1, null=True, blank=True)),
            ('last_paid_subscription', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'thedaily', ['Subscriber'])

        # Adding M2M table for field newsletters on 'Subscriber'
        m2m_table_name = db.shorten_name(u'thedaily_subscriber_newsletters')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('subscriber', models.ForeignKey(orm[u'thedaily.subscriber'], null=False)),
            ('publication', models.ForeignKey(orm[u'core.publication'], null=False))
        ))
        db.create_unique(m2m_table_name, ['subscriber_id', 'publication_id'])

        # Adding M2M table for field category_newsletters on 'Subscriber'
        m2m_table_name = db.shorten_name(u'thedaily_subscriber_category_newsletters')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('subscriber', models.ForeignKey(orm[u'thedaily.subscriber'], null=False)),
            ('category', models.ForeignKey(orm[u'core.category'], null=False))
        ))
        db.create_unique(m2m_table_name, ['subscriber_id', 'category_id'])

        # Adding model 'OAuthState'
        db.create_table(u'thedaily_oauthstate', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('state', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('fullname', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal(u'thedaily', ['OAuthState'])

        # Adding model 'WebSubscriber'
        db.create_table(u'thedaily_websubscriber', (
            (u'subscriber_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['thedaily.Subscriber'], unique=True, primary_key=True)),
            ('referrer', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='referred', null=True, to=orm['thedaily.Subscriber'])),
        ))
        db.send_create_signal(u'thedaily', ['WebSubscriber'])

        # Adding model 'SubscriberEditionDownloads'
        db.create_table(u'thedaily_subscribereditiondownloads', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subscriber', self.gf('django.db.models.fields.related.ForeignKey')(related_name='edition_downloads', to=orm['thedaily.Subscriber'])),
            ('edition', self.gf('django.db.models.fields.related.ForeignKey')(related_name='subscribers_downloads', to=orm['core.Edition'])),
            ('downloads', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal(u'thedaily', ['SubscriberEditionDownloads'])

        # Adding unique constraint on 'SubscriberEditionDownloads', fields ['subscriber', 'edition']
        db.create_unique(u'thedaily_subscribereditiondownloads', ['subscriber_id', 'edition_id'])

        # Adding model 'SentMail'
        db.create_table(u'thedaily_sentmail', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subscriber', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['thedaily.Subscriber'])),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('date_sent', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'thedaily', ['SentMail'])

        # Adding model 'SubscriberEvent'
        db.create_table(u'thedaily_subscriberevent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subscriber', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['thedaily.Subscriber'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('date_occurred', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'thedaily', ['SubscriberEvent'])

        # Adding model 'EditionDownload'
        db.create_table(u'thedaily_editiondownload', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subscriber', self.gf('django.db.models.fields.related.ForeignKey')(related_name='subscriber_downloads', to=orm['thedaily.SubscriberEditionDownloads'])),
            ('incomplete', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('download_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'thedaily', ['EditionDownload'])

        # Adding unique constraint on 'EditionDownload', fields ['subscriber', 'download_date']
        db.create_unique(u'thedaily_editiondownload', ['subscriber_id', 'download_date'])

        # Adding model 'Subscription'
        db.create_table(u'thedaily_subscription', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subscriber', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='suscripciones', null=True, to=orm['auth.User'])),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('document', self.gf('django.db.models.fields.CharField')(max_length=11, null=True)),
            ('telephone', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('province', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('observations', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('subscription_type', self.gf('django.db.models.fields.CharField')(default='DIG', max_length=3)),
            ('subscription_plan', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('subscription_end', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('credit_card', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
            ('friend1_name', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('friend1_email', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('friend1_telephone', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('friend2_name', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('friend2_email', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('friend2_telephone', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('friend3_name', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('friend3_email', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('friend3_telephone', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('public_profile', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('promo_code', self.gf('django.db.models.fields.CharField')(max_length=8, null=True, blank=True)),
        ))
        db.send_create_signal(u'thedaily', ['Subscription'])

        # Adding M2M table for field subscription_type_prices on 'Subscription'
        m2m_table_name = db.shorten_name(u'thedaily_subscription_subscription_type_prices')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('subscription', models.ForeignKey(orm[u'thedaily.subscription'], null=False)),
            ('subscriptionprices', models.ForeignKey(orm[u'thedaily.subscriptionprices'], null=False))
        ))
        db.create_unique(m2m_table_name, ['subscription_id', 'subscriptionprices_id'])

        # Adding model 'PollAnswer'
        db.create_table(u'thedaily_pollanswer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('document', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('answer', self.gf('django.db.models.fields.CharField')(max_length=16)),
        ))
        db.send_create_signal(u'thedaily', ['PollAnswer'])

        # Adding model 'UsersApiSession'
        db.create_table(u'thedaily_usersapisession', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='api_sessions', to=orm['auth.User'])),
            ('udid', self.gf('django.db.models.fields.CharField')(max_length=16)),
        ))
        db.send_create_signal(u'thedaily', ['UsersApiSession'])


    def backwards(self, orm):
        # Removing unique constraint on 'EditionDownload', fields ['subscriber', 'download_date']
        db.delete_unique(u'thedaily_editiondownload', ['subscriber_id', 'download_date'])

        # Removing unique constraint on 'SubscriberEditionDownloads', fields ['subscriber', 'edition']
        db.delete_unique(u'thedaily_subscribereditiondownloads', ['subscriber_id', 'edition_id'])

        # Deleting model 'SubscriptionPrices'
        db.delete_table(u'thedaily_subscriptionprices')

        # Deleting model 'Subscriber'
        db.delete_table(u'thedaily_subscriber')

        # Removing M2M table for field newsletters on 'Subscriber'
        db.delete_table(db.shorten_name(u'thedaily_subscriber_newsletters'))

        # Removing M2M table for field category_newsletters on 'Subscriber'
        db.delete_table(db.shorten_name(u'thedaily_subscriber_category_newsletters'))

        # Deleting model 'OAuthState'
        db.delete_table(u'thedaily_oauthstate')

        # Deleting model 'WebSubscriber'
        db.delete_table(u'thedaily_websubscriber')

        # Deleting model 'SubscriberEditionDownloads'
        db.delete_table(u'thedaily_subscribereditiondownloads')

        # Deleting model 'SentMail'
        db.delete_table(u'thedaily_sentmail')

        # Deleting model 'SubscriberEvent'
        db.delete_table(u'thedaily_subscriberevent')

        # Deleting model 'EditionDownload'
        db.delete_table(u'thedaily_editiondownload')

        # Deleting model 'Subscription'
        db.delete_table(u'thedaily_subscription')

        # Removing M2M table for field subscription_type_prices on 'Subscription'
        db.delete_table(db.shorten_name(u'thedaily_subscription_subscription_type_prices'))

        # Deleting model 'PollAnswer'
        db.delete_table(u'thedaily_pollanswer')

        # Deleting model 'UsersApiSession'
        db.delete_table(u'thedaily_usersapisession')


    models = {
        u'actstream.action': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': u"orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.category': {
            'Meta': {'ordering': "('order', 'name')", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'full_width_cover_image': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['photologue.Photo']", 'null': 'True', 'blank': 'True'}),
            'full_width_cover_image_lead': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'full_width_cover_image_title': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'has_newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'more_link_title': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '16'}),
            'new_pill': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'core.edition': {
            'Meta': {'ordering': "('-date_published',)", 'object_name': 'Edition'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'cover': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2020, 12, 14, 0, 0)'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pdf': ('django.db.models.fields.files.FileField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'pdf_md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'publication': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'core_edition'", 'to': u"orm['core.Publication']"}),
            'title': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        u'core.portabledocumentformatpage': {
            'Meta': {'ordering': "('content_type', 'object_id', 'number')", 'unique_together': "(('content_type', 'object_id', 'number'),)", 'object_name': 'PortableDocumentFormatPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'pdf': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'snapshot': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        u'core.publication': {
            'Meta': {'ordering': "['weight']", 'object_name': 'Publication'},
            'apple_touch_icon_180': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'apple_touch_icon_192': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'apple_touch_icon_512': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'full_width_cover_image': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['photologue.Photo']", 'null': 'True', 'blank': 'True'}),
            'has_newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'icon': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'icon_png': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'icon_png_16': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'icon_png_32': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'is_emergente': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'newsletter_campaign': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'newsletter_header_color': ('django.db.models.fields.CharField', [], {'default': "u'#262626'", 'max_length': '7'}),
            'open_graph_image': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'subscribe_box_nl_subscribe_anon': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'subscribe_box_nl_subscribe_auth': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'subscribe_box_question': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'})
        },
        u'photologue.photo': {
            'Meta': {'ordering': "['-date_added']", 'object_name': 'Photo'},
            'caption': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'crop_from': ('django.db.models.fields.CharField', [], {'default': "'center'", 'max_length': '10', 'blank': 'True'}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'effect': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'photo_related'", 'null': 'True', 'to': u"orm['photologue.PhotoEffect']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'title_slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'view_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        u'photologue.photoeffect': {
            'Meta': {'object_name': 'PhotoEffect'},
            'background_color': ('django.db.models.fields.CharField', [], {'default': "'#FFFFFF'", 'max_length': '7'}),
            'brightness': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'color': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'contrast': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'filters': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'reflection_size': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'reflection_strength': ('django.db.models.fields.FloatField', [], {'default': '0.6'}),
            'sharpness': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'transpose_method': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'})
        },
        u'thedaily.editiondownload': {
            'Meta': {'unique_together': "(('subscriber', 'download_date'),)", 'object_name': 'EditionDownload'},
            'download_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'incomplete': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'subscriber': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscriber_downloads'", 'to': u"orm['thedaily.SubscriberEditionDownloads']"})
        },
        u'thedaily.oauthstate': {
            'Meta': {'object_name': 'OAuthState'},
            'fullname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'thedaily.pollanswer': {
            'Meta': {'object_name': 'PollAnswer'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'document': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'thedaily.sentmail': {
            'Meta': {'object_name': 'SentMail'},
            'date_sent': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'subscriber': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['thedaily.Subscriber']"})
        },
        u'thedaily.subscriber': {
            'Meta': {'object_name': 'Subscriber'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_polls': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'allow_promotions': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'category_newsletters': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['core.Category']", 'symmetrical': 'False', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'costumer_id': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'days': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '5', 'null': 'True'}),
            'document': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_paid_subscription': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'lento_pdf': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'newsletters': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['core.Publication']", 'symmetrical': 'False', 'blank': 'True'}),
            'pdf': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'plan_id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'profile_photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'province': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'ruta': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'ruta_fs': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'ruta_lento': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscription_mode': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'subscriber'", 'unique': 'True', 'null': 'True', 'to': u"orm['auth.User']"})
        },
        u'thedaily.subscribereditiondownloads': {
            'Meta': {'ordering': "('-edition', '-downloads', 'subscriber')", 'unique_together': "(('subscriber', 'edition'),)", 'object_name': 'SubscriberEditionDownloads'},
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'edition': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscribers_downloads'", 'to': u"orm['core.Edition']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subscriber': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'edition_downloads'", 'to': u"orm['thedaily.Subscriber']"})
        },
        u'thedaily.subscriberevent': {
            'Meta': {'object_name': 'SubscriberEvent'},
            'date_occurred': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subscriber': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['thedaily.Subscriber']"})
        },
        u'thedaily.subscription': {
            'Meta': {'ordering': "('-date_created', 'first_name', 'last_name')", 'object_name': 'Subscription'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'credit_card': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'document': ('django.db.models.fields.CharField', [], {'max_length': '11', 'null': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'friend1_email': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'friend1_name': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'friend1_telephone': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'friend2_email': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'friend2_name': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'friend2_telephone': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'friend3_email': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'friend3_name': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'friend3_telephone': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'observations': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'promo_code': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'blank': 'True'}),
            'province': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'public_profile': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'subscriber': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'suscripciones'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'subscription_end': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'subscription_plan': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'subscription_type': ('django.db.models.fields.CharField', [], {'default': "'DIG'", 'max_length': '3'}),
            'subscription_type_prices': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['thedaily.SubscriptionPrices']", 'symmetrical': 'False', 'blank': 'True'}),
            'telephone': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'thedaily.subscriptionprices': {
            'Meta': {'ordering': "['order']", 'object_name': 'SubscriptionPrices'},
            'auth_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'ga_category': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'ga_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'ga_sku': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'paypal_button_id': ('django.db.models.fields.CharField', [], {'max_length': '13', 'null': 'True', 'blank': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'publication': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Publication']", 'null': 'True', 'blank': 'True'}),
            'subscription_type': ('django.db.models.fields.CharField', [], {'default': "'PAPYDIM'", 'unique': 'True', 'max_length': '7'})
        },
        u'thedaily.usersapisession': {
            'Meta': {'object_name': 'UsersApiSession'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'udid': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'api_sessions'", 'to': u"orm['auth.User']"})
        },
        u'thedaily.websubscriber': {
            'Meta': {'object_name': 'WebSubscriber', '_ormbases': [u'thedaily.Subscriber']},
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'referred'", 'null': 'True', 'to': u"orm['thedaily.Subscriber']"}),
            u'subscriber_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['thedaily.Subscriber']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['thedaily']