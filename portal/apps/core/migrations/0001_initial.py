# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Publication'
        db.create_table(u'core_publication', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('weight', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('has_newsletter', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('newsletter_header_color', self.gf('django.db.models.fields.CharField')(default=u'#262626', max_length=7)),
            ('newsletter_campaign', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('full_width_cover_image', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['photologue.Photo'], null=True, blank=True)),
            ('is_emergente', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'core', ['Publication'])

        # Adding model 'PortableDocumentFormatPage'
        db.create_table(u'core_portabledocumentformatpage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('number', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('pdf', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('snapshot', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['PortableDocumentFormatPage'])

        # Adding unique constraint on 'PortableDocumentFormatPage', fields ['content_type', 'object_id', 'number']
        db.create_unique(u'core_portabledocumentformatpage', ['content_type_id', 'object_id', 'number'])

        # Adding model 'PortableDocumentFormatPageImage'
        db.create_table(u'core_portabledocumentformatpageimage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='images', to=orm['core.PortableDocumentFormatPage'])),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('number', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['PortableDocumentFormatPageImage'])

        # Adding model 'Edition'
        db.create_table(u'core_edition', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pdf', self.gf('django.db.models.fields.files.FileField')(max_length=150, null=True, blank=True)),
            ('pdf_md5', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('downloads', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('cover', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('date_published', self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2020, 11, 6, 0, 0))),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('title', self.gf('django.db.models.fields.TextField')(null=True)),
            ('publication', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'core_edition', to=orm['core.Publication'])),
        ))
        db.send_create_signal(u'core', ['Edition'])

        # Adding model 'Supplement'
        db.create_table(u'core_supplement', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pdf', self.gf('django.db.models.fields.files.FileField')(max_length=150, null=True, blank=True)),
            ('pdf_md5', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('downloads', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('cover', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('date_published', self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2020, 11, 6, 0, 0))),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('edition', self.gf('django.db.models.fields.related.ForeignKey')(related_name='supplements', to=orm['core.Edition'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'core', ['Supplement'])

        # Adding unique constraint on 'Supplement', fields ['date_published', 'name']
        db.create_unique(u'core_supplement', ['date_published', 'name'])

        # Adding model 'Category'
        db.create_table(u'core_category', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=16)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=16, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('order', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('has_newsletter', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('more_link_title', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('new_pill', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('full_width_cover_image', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['photologue.Photo'], null=True, blank=True)),
            ('full_width_cover_image_title', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('full_width_cover_image_lead', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['Category'])

        # Adding model 'Section'
        db.create_table(u'core_section', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Category'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('name_in_category_menu', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('contact', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('home_order', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('in_home', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('imagen', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('home_block_all_pubs', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('home_block_show_featured', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('background_color', self.gf('django.db.models.fields.CharField')(default='#ffffff', max_length=7)),
            ('white_text', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('show_description', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('show_image', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'core', ['Section'])

        # Adding M2M table for field publications on 'Section'
        m2m_table_name = db.shorten_name(u'core_section_publications')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('section', models.ForeignKey(orm[u'core.section'], null=False)),
            ('publication', models.ForeignKey(orm[u'core.publication'], null=False))
        ))
        db.create_unique(m2m_table_name, ['section_id', 'publication_id'])

        # Adding model 'Journalist'
        db.create_table(u'core_journalist', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('job', self.gf('django.db.models.fields.CharField')(default='PE', max_length=2)),
            ('bio', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('fb', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('tt', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('gp', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('ig', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['Journalist'])

        # Adding M2M table for field sections on 'Journalist'
        m2m_table_name = db.shorten_name(u'core_journalist_sections')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('journalist', models.ForeignKey(orm[u'core.journalist'], null=False)),
            ('section', models.ForeignKey(orm[u'core.section'], null=False))
        ))
        db.create_unique(m2m_table_name, ['journalist_id', 'section_id'])

        # Adding model 'Location'
        db.create_table(u'core_location', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['Location'])

        # Adding unique constraint on 'Location', fields ['city', 'country']
        db.create_unique(u'core_location', ['city', 'country'])

        # Adding model 'Article'
        db.create_table(u'core_article', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('publication', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name=u'articles_core', null=True, to=orm['core.Publication'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('keywords', self.gf('django.db.models.fields.CharField')(max_length=45, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=200)),
            ('url_path', self.gf('django.db.models.fields.CharField')(max_length=512, db_index=True)),
            ('deck', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('lead', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('header_display', self.gf('django.db.models.fields.CharField')(default='BG', max_length=2, null=True, blank=True)),
            ('home_header_display', self.gf('django.db.models.fields.CharField')(default='SM', max_length=2, null=True, blank=True)),
            ('home_lead', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('home_display', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
            ('home_top_deck', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('only_initials', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('latitude', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=10, decimal_places=6, blank=True)),
            ('longitude', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=10, decimal_places=6, blank=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name=u'articles_core', null=True, to=orm['core.Location'])),
            ('is_published', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('date_published', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2020, 11, 6, 0, 0))),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('views', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, db_index=True)),
            ('allow_comments', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'created_articles_core', null=True, to=orm['auth.User'])),
            ('photo', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['photologue.Photo'], null=True, blank=True)),
            ('gallery', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['photologue.Gallery'], null=True, blank=True)),
            ('video', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name=u'articles_core', null=True, to=orm['videologue.Video'])),
            ('youtube_video', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['videologue.YouTubeVideo'], null=True, blank=True)),
            ('audio', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name=u'articles_core', null=True, to=orm['audiologue.Audio'])),
            ('tags', self.gf('tagging.fields.TagField')(null=True)),
            ('allow_related', self.gf('django.db.models.fields.BooleanField')(default=True, db_index=True)),
            ('show_related_articles', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('main_section', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='main', null=True, on_delete=models.SET_NULL, to=orm['core.ArticleRel'])),
            ('continues', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='continuation', null=True, to=orm['core.Article'])),
            ('newsletter_featured', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'core', ['Article'])

        # Adding M2M table for field byline on 'Article'
        m2m_table_name = db.shorten_name(u'core_article_byline')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('article', models.ForeignKey(orm[u'core.article'], null=False)),
            ('journalist', models.ForeignKey(orm[u'core.journalist'], null=False))
        ))
        db.create_unique(m2m_table_name, ['article_id', 'journalist_id'])

        # Adding model 'ArticleRel'
        db.create_table(u'core_articlerel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('article', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Article'])),
            ('edition', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Edition'])),
            ('section', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Section'])),
            ('position', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=None, null=True)),
            ('home_top', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('top_position', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['ArticleRel'])

        # Adding model 'ArticleViewedBy'
        db.create_table(u'core_articleviewedby', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('article', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Article'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('viewed_at', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
        ))
        db.send_create_signal(u'core', ['ArticleViewedBy'])

        # Adding unique constraint on 'ArticleViewedBy', fields ['article', 'user']
        db.create_unique(u'core_articleviewedby', ['article_id', 'user_id'])

        # Adding model 'ArticleExtension'
        db.create_table(u'core_articleextension', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('article', self.gf('django.db.models.fields.related.ForeignKey')(related_name='extensions', to=orm['core.Article'])),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('size', self.gf('django.db.models.fields.CharField')(default='R', max_length=1)),
            ('background_color', self.gf('django.db.models.fields.CharField')(default='#eaeaea', max_length=7, null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['ArticleExtension'])

        # Adding model 'ArticleBodyImage'
        db.create_table(u'core_articlebodyimage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('article', self.gf('django.db.models.fields.related.ForeignKey')(related_name='body_image', to=orm['core.Article'])),
            ('image', self.gf('django.db.models.fields.related.ForeignKey')(related_name='photo', to=orm['photologue.Photo'])),
            ('display', self.gf('django.db.models.fields.CharField')(default='MD', max_length=2)),
        ))
        db.send_create_signal(u'core', ['ArticleBodyImage'])

        # Adding model 'PrintOnlyArticle'
        db.create_table(u'core_printonlyarticle', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('deck', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('edition', self.gf('django.db.models.fields.related.ForeignKey')(related_name='print_only_articles', to=orm['core.Edition'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['PrintOnlyArticle'])

        # Adding unique constraint on 'PrintOnlyArticle', fields ['headline', 'edition']
        db.create_unique(u'core_printonlyarticle', ['headline', 'edition_id'])

        # Adding model 'ArticleUrlHistory'
        db.create_table(u'core_articleurlhistory', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('article', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Article'])),
            ('absolute_url', self.gf('django.db.models.fields.URLField')(max_length=500, db_index=True)),
        ))
        db.send_create_signal(u'core', ['ArticleUrlHistory'])

        # Adding unique constraint on 'ArticleUrlHistory', fields ['article', 'absolute_url']
        db.create_unique(u'core_articleurlhistory', ['article_id', 'absolute_url'])

        # Adding model 'BreakingNewsModule'
        db.create_table(u'core_breakingnewsmodule', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('is_published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('deck', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('enable_notification', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('notification_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('notification_text', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('embeds_headline', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embeds_description', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('embed1_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed1_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed2_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed2_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed3_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed3_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed4_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed4_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed5_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed5_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed6_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed6_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed7_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed7_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed8_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed8_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed9_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed9_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed10_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed10_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed11_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed11_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed12_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed12_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed13_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed13_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('embed14_title', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('embed14_content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['BreakingNewsModule'])

        # Adding M2M table for field articles on 'BreakingNewsModule'
        m2m_table_name = db.shorten_name(u'core_breakingnewsmodule_articles')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('breakingnewsmodule', models.ForeignKey(orm[u'core.breakingnewsmodule'], null=False)),
            ('article', models.ForeignKey(orm[u'core.article'], null=False))
        ))
        db.create_unique(m2m_table_name, ['breakingnewsmodule_id', 'article_id'])

        # Adding M2M table for field publications on 'BreakingNewsModule'
        m2m_table_name = db.shorten_name(u'core_breakingnewsmodule_publications')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('breakingnewsmodule', models.ForeignKey(orm[u'core.breakingnewsmodule'], null=False)),
            ('publication', models.ForeignKey(orm[u'core.publication'], null=False))
        ))
        db.create_unique(m2m_table_name, ['breakingnewsmodule_id', 'publication_id'])

        # Adding M2M table for field categories on 'BreakingNewsModule'
        m2m_table_name = db.shorten_name(u'core_breakingnewsmodule_categories')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('breakingnewsmodule', models.ForeignKey(orm[u'core.breakingnewsmodule'], null=False)),
            ('category', models.ForeignKey(orm[u'core.category'], null=False))
        ))
        db.create_unique(m2m_table_name, ['breakingnewsmodule_id', 'category_id'])

        # Adding model 'Home'
        db.create_table(u'core_home', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(related_name='home', unique=True, to=orm['core.Category'])),
            ('cover', self.gf('django.db.models.fields.related.ForeignKey')(related_name='is_cover_on', to=orm['core.Article'])),
            ('fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('core', ['Home'])

        # Adding model 'Module'
        db.create_table(u'core_module', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('home', self.gf('django.db.models.fields.related.ForeignKey')(related_name='modules', unique=True, to=orm['core.Home'])),
            ('article_1', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='module_1', null=True, on_delete=models.SET_NULL, to=orm['core.Article'])),
            ('article_1_fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('article_2', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='module_2', null=True, on_delete=models.SET_NULL, to=orm['core.Article'])),
            ('article_2_fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('article_3', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='module_3', null=True, on_delete=models.SET_NULL, to=orm['core.Article'])),
            ('article_3_fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('article_4', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='module_4', null=True, on_delete=models.SET_NULL, to=orm['core.Article'])),
            ('article_4_fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('article_5', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='module_5', null=True, on_delete=models.SET_NULL, to=orm['core.Article'])),
            ('article_5_fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('article_6', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='module_6', null=True, on_delete=models.SET_NULL, to=orm['core.Article'])),
            ('article_6_fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('article_7', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='module_7', null=True, on_delete=models.SET_NULL, to=orm['core.Article'])),
            ('article_7_fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('article_8', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='module_8', null=True, on_delete=models.SET_NULL, to=orm['core.Article'])),
            ('article_8_fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('article_9', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='module_9', null=True, on_delete=models.SET_NULL, to=orm['core.Article'])),
            ('article_9_fixed', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('core', ['Module'])


    def backwards(self, orm):
        # Removing unique constraint on 'ArticleUrlHistory', fields ['article', 'absolute_url']
        db.delete_unique(u'core_articleurlhistory', ['article_id', 'absolute_url'])

        # Removing unique constraint on 'PrintOnlyArticle', fields ['headline', 'edition']
        db.delete_unique(u'core_printonlyarticle', ['headline', 'edition_id'])

        # Removing unique constraint on 'ArticleViewedBy', fields ['article', 'user']
        db.delete_unique(u'core_articleviewedby', ['article_id', 'user_id'])

        # Removing unique constraint on 'Location', fields ['city', 'country']
        db.delete_unique(u'core_location', ['city', 'country'])

        # Removing unique constraint on 'Supplement', fields ['date_published', 'name']
        db.delete_unique(u'core_supplement', ['date_published', 'name'])

        # Removing unique constraint on 'PortableDocumentFormatPage', fields ['content_type', 'object_id', 'number']
        db.delete_unique(u'core_portabledocumentformatpage', ['content_type_id', 'object_id', 'number'])

        # Deleting model 'Publication'
        db.delete_table(u'core_publication')

        # Deleting model 'PortableDocumentFormatPage'
        db.delete_table(u'core_portabledocumentformatpage')

        # Deleting model 'PortableDocumentFormatPageImage'
        db.delete_table(u'core_portabledocumentformatpageimage')

        # Deleting model 'Edition'
        db.delete_table(u'core_edition')

        # Deleting model 'Supplement'
        db.delete_table(u'core_supplement')

        # Deleting model 'Category'
        db.delete_table(u'core_category')

        # Deleting model 'Section'
        db.delete_table(u'core_section')

        # Removing M2M table for field publications on 'Section'
        db.delete_table(db.shorten_name(u'core_section_publications'))

        # Deleting model 'Journalist'
        db.delete_table(u'core_journalist')

        # Removing M2M table for field sections on 'Journalist'
        db.delete_table(db.shorten_name(u'core_journalist_sections'))

        # Deleting model 'Location'
        db.delete_table(u'core_location')

        # Deleting model 'Article'
        db.delete_table(u'core_article')

        # Removing M2M table for field byline on 'Article'
        db.delete_table(db.shorten_name(u'core_article_byline'))

        # Deleting model 'ArticleRel'
        db.delete_table(u'core_articlerel')

        # Deleting model 'ArticleViewedBy'
        db.delete_table(u'core_articleviewedby')

        # Deleting model 'ArticleExtension'
        db.delete_table(u'core_articleextension')

        # Deleting model 'ArticleBodyImage'
        db.delete_table(u'core_articlebodyimage')

        # Deleting model 'PrintOnlyArticle'
        db.delete_table(u'core_printonlyarticle')

        # Deleting model 'ArticleUrlHistory'
        db.delete_table(u'core_articleurlhistory')

        # Deleting model 'BreakingNewsModule'
        db.delete_table(u'core_breakingnewsmodule')

        # Removing M2M table for field articles on 'BreakingNewsModule'
        db.delete_table(db.shorten_name(u'core_breakingnewsmodule_articles'))

        # Removing M2M table for field publications on 'BreakingNewsModule'
        db.delete_table(db.shorten_name(u'core_breakingnewsmodule_publications'))

        # Removing M2M table for field categories on 'BreakingNewsModule'
        db.delete_table(db.shorten_name(u'core_breakingnewsmodule_categories'))

        # Deleting model 'Home'
        db.delete_table(u'core_home')

        # Deleting model 'Module'
        db.delete_table(u'core_module')


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
            'date_published': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2020, 11, 6, 0, 0)'}),
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
            'content': ('django.db.models.fields.TextField', [], {}),
            'cover': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2020, 11, 6, 0, 0)'}),
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
        u'core.portabledocumentformatpageimage': {
            'Meta': {'ordering': "('-date_created', 'page', 'number', 'id')", 'object_name': 'PortableDocumentFormatPageImage'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'images'", 'to': u"orm['core.PortableDocumentFormatPage']"})
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
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'full_width_cover_image': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['photologue.Photo']", 'null': 'True', 'blank': 'True'}),
            'has_newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'is_emergente': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'newsletter_campaign': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'newsletter_header_color': ('django.db.models.fields.CharField', [], {'default': "u'#262626'", 'max_length': '7'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
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
            'content': ('django.db.models.fields.TextField', [], {}),
            'cover': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2020, 11, 6, 0, 0)'}),
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