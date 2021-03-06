# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'PortableDocumentFormatPage', fields ['content_type', 'object_id', 'number']
        db.delete_unique(u'core_portabledocumentformatpage', ['content_type_id', 'object_id', 'number'])

        # Deleting model 'PortableDocumentFormatPageImage'
        db.delete_table(u'core_portabledocumentformatpageimage')

        # Deleting model 'PortableDocumentFormatPage'
        db.delete_table(u'core_portabledocumentformatpage')

        # Deleting field 'Supplement.content'
        db.delete_column(u'core_supplement', 'content')

        # Deleting field 'Edition.content'
        db.delete_column(u'core_edition', 'content')


    def backwards(self, orm):
        # Adding model 'PortableDocumentFormatPageImage'
        db.create_table(u'core_portabledocumentformatpageimage', (
            ('number', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='images', to=orm['core.PortableDocumentFormatPage'])),
        ))
        db.send_create_signal(u'core', ['PortableDocumentFormatPageImage'])

        # Adding model 'PortableDocumentFormatPage'
        db.create_table(u'core_portabledocumentformatpage', (
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('snapshot', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('pdf', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
        ))
        db.send_create_signal(u'core', ['PortableDocumentFormatPage'])

        # Adding unique constraint on 'PortableDocumentFormatPage', fields ['content_type', 'object_id', 'number']
        db.create_unique(u'core_portabledocumentformatpage', ['content_type_id', 'object_id', 'number'])


        # User chose to not deal with backwards NULL issues for 'Supplement.content'
        raise RuntimeError("Cannot reverse this migration. 'Supplement.content' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'Supplement.content'
        db.add_column(u'core_supplement', 'content',
                      self.gf('django.db.models.fields.TextField')(),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Edition.content'
        raise RuntimeError("Cannot reverse this migration. 'Edition.content' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'Edition.content'
        db.add_column(u'core_edition', 'content',
                      self.gf('django.db.models.fields.TextField')(),
                      keep_default=False)


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
        u'audiologue.audio': {
            'Meta': {'object_name': 'Audio'},
            'byline': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_uploaded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'times_viewed': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
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
        u'core.article': {
            'Meta': {'ordering': "('-date_published',)", 'object_name': 'Article'},
            'allow_comments': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'allow_related': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'audio': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'articles_core'", 'null': 'True', 'to': u"orm['audiologue.Audio']"}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'byline': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "u'articles_core'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['core.Journalist']"}),
            'continues': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'continuation'", 'null': 'True', 'to': u"orm['core.Article']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'created_articles_core'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2020, 12, 26, 0, 0)'}),
            'deck': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'gallery': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['photologue.Gallery']", 'null': 'True', 'blank': 'True'}),
            'header_display': ('django.db.models.fields.CharField', [], {'default': "'BG'", 'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'home_display': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'home_header_display': ('django.db.models.fields.CharField', [], {'default': "'SM'", 'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'home_lead': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'home_top_deck': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'keywords': ('django.db.models.fields.CharField', [], {'max_length': '45', 'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'latitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '6', 'blank': 'True'}),
            'lead': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'articles_core'", 'null': 'True', 'to': u"orm['core.Location']"}),
            'longitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '6', 'blank': 'True'}),
            'main_section': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'main'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.ArticleRel']"}),
            'newsletter_featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'only_initials': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'photo': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['photologue.Photo']", 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publication': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'articles_core'", 'null': 'True', 'to': u"orm['core.Publication']"}),
            'sections': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'articles_core'", 'null': 'True', 'through': u"orm['core.ArticleRel']", 'to': u"orm['core.Section']"}),
            'show_related_articles': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200'}),
            'tags': ('tagging.fields.TagField', [], {'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'url_path': ('django.db.models.fields.CharField', [], {'max_length': '512', 'db_index': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'articles_core'", 'null': 'True', 'to': u"orm['videologue.Video']"}),
            'viewed_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "u'viewed_articles_core'", 'to': u"orm['auth.User']", 'through': u"orm['core.ArticleViewedBy']", 'blank': 'True', 'symmetrical': 'False', 'null': 'True'}),
            'views': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'youtube_video': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['videologue.YouTubeVideo']", 'null': 'True', 'blank': 'True'})
        },
        u'core.articlebodyimage': {
            'Meta': {'object_name': 'ArticleBodyImage'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'body_image'", 'to': u"orm['core.Article']"}),
            'display': ('django.db.models.fields.CharField', [], {'default': "'MD'", 'max_length': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photo'", 'to': u"orm['photologue.Photo']"})
        },
        u'core.articleextension': {
            'Meta': {'ordering': "('article', 'headline')", 'object_name': 'ArticleExtension'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'extensions'", 'to': u"orm['core.Article']"}),
            'background_color': ('django.db.models.fields.CharField', [], {'default': "'#eaeaea'", 'max_length': '7', 'null': 'True', 'blank': 'True'}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'size': ('django.db.models.fields.CharField', [], {'default': "'R'", 'max_length': '1'})
        },
        u'core.articlerel': {
            'Meta': {'ordering': "('position', '-article__date_published')", 'object_name': 'ArticleRel'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Article']"}),
            'edition': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Edition']"}),
            'home_top': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': 'None', 'null': 'True'}),
            'section': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Section']"}),
            'top_position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'core.articleurlhistory': {
            'Meta': {'unique_together': "(('article', 'absolute_url'),)", 'object_name': 'ArticleUrlHistory'},
            'absolute_url': ('django.db.models.fields.URLField', [], {'max_length': '500', 'db_index': 'True'}),
            'article': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Article']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'core.articleviewedby': {
            'Meta': {'unique_together': "(('article', 'user'),)", 'object_name': 'ArticleViewedBy'},
            'article': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Article']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'viewed_at': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        u'core.breakingnewsmodule': {
            'Meta': {'object_name': 'BreakingNewsModule'},
            'articles': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['core.Article']", 'symmetrical': 'False', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['core.Category']", 'null': 'True', 'blank': 'True'}),
            'deck': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'embed10_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed10_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed11_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed11_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed12_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed12_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed13_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed13_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed14_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed14_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed1_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed1_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed2_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed2_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed3_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed3_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed4_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed4_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed5_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed5_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed6_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed6_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed7_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed7_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed8_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed8_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embed9_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'embed9_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'embeds_description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'embeds_headline': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'enable_notification': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'notification_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notification_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'publications': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['core.Publication']", 'null': 'True', 'blank': 'True'})
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
            'cover': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2020, 12, 26, 0, 0)'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pdf': ('django.db.models.fields.files.FileField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'pdf_md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'publication': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'core_edition'", 'to': u"orm['core.Publication']"}),
            'title': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'core.home': {
            'Meta': {'ordering': "('category',)", 'object_name': 'Home'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'home'", 'unique': 'True', 'to': u"orm['core.Category']"}),
            'cover': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'is_cover_on'", 'to': u"orm['core.Article']"}),
            'fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'core.journalist': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Journalist'},
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'fb': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'gp': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ig': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'job': ('django.db.models.fields.CharField', [], {'default': "'PE'", 'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'sections': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['core.Section']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'tt': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        u'core.location': {
            'Meta': {'ordering': "('country', 'city')", 'unique_together': "(('city', 'country'),)", 'object_name': 'Location'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'core.module': {
            'Meta': {'ordering': "('home',)", 'object_name': 'Module'},
            'article_1': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'module_1'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.Article']"}),
            'article_1_fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'article_2': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'module_2'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.Article']"}),
            'article_2_fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'article_3': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'module_3'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.Article']"}),
            'article_3_fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'article_4': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'module_4'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.Article']"}),
            'article_4_fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'article_5': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'module_5'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.Article']"}),
            'article_5_fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'article_6': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'module_6'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.Article']"}),
            'article_6_fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'article_7': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'module_7'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.Article']"}),
            'article_7_fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'article_8': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'module_8'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.Article']"}),
            'article_8_fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'article_9': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'module_9'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['core.Article']"}),
            'article_9_fixed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'home': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'modules'", 'unique': 'True', 'to': "orm['core.Home']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'core.printonlyarticle': {
            'Meta': {'ordering': "('id',)", 'unique_together': "(('headline', 'edition'),)", 'object_name': 'PrintOnlyArticle'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deck': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'edition': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'print_only_articles'", 'to': u"orm['core.Edition']"}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
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
            'open_graph_image_height': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'open_graph_image_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'publisher_logo': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'publisher_logo_height': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_logo_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'subscribe_box_nl_subscribe_anon': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'subscribe_box_nl_subscribe_auth': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'subscribe_box_question': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'weight': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'})
        },
        u'core.section': {
            'Meta': {'ordering': "('home_order', 'name', 'date_created')", 'object_name': 'Section'},
            'background_color': ('django.db.models.fields.CharField', [], {'default': "'#ffffff'", 'max_length': '7'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Category']", 'null': 'True', 'blank': 'True'}),
            'contact': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'home_block_all_pubs': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'home_block_show_featured': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'home_order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imagen': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'in_home': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'name_in_category_menu': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'publications': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['core.Publication']", 'null': 'True', 'blank': 'True'}),
            'show_description': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_image': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'white_text': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'core.supplement': {
            'Meta': {'ordering': "('-date_published', 'name')", 'unique_together': "(('date_published', 'name'),)", 'object_name': 'Supplement'},
            'cover': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2020, 12, 26, 0, 0)'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'edition': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'supplements'", 'to': u"orm['core.Edition']"}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'pdf': ('django.db.models.fields.files.FileField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'pdf_md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'photologue.gallery': {
            'Meta': {'ordering': "['-date_added']", 'object_name': 'Gallery'},
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'photos': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'galleries'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['photologue.Photo']"}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'title_slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
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
        u'videologue.video': {
            'Meta': {'object_name': 'Video'},
            'byline': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_uploaded': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'times_viewed': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'videologue.youtubevideo': {
            'Meta': {'object_name': 'YouTubeVideo'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'}),
            'yt_id': ('django.db.models.fields.CharField', [], {'max_length': '11', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['core']