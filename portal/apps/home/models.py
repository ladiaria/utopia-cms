# -*- coding: utf-8 -*-
from operator import itemgetter

from django.db.models import Model, ForeignKey, TextField, CharField, DateTimeField, BooleanField, SET_NULL

from core.models import Category, Article


class Home(Model):
    category = ForeignKey(Category, verbose_name=u'área', unique=True, related_name='home')
    cover = ForeignKey(Article, verbose_name=u'artículo principal', related_name='is_cover_on')
    fixed = BooleanField('fijo')

    def __unicode__(self):
        return u'%s - %s' % (self.category, self.cover)

    def last_published(self):
        return self.cover.last_published_by_category(self.category)

    class Meta:
        verbose_name = u'portada de área'
        verbose_name_plural = u'portadas de área'
        app_label = 'core'
        ordering = ('category', )


class HomeArticle(Model):

    DISPLAY_CHOICES = (
        ('I', u'Imagen'),
        ('A', u'Audio'),
        ('V', u'Video'),
    )

    article = ForeignKey(Article, verbose_name=u'artículo', unique=True)
    lead = TextField(u'copete', blank=True, null=True)
    display = CharField(u'mostrar', max_length=1, choices=DISPLAY_CHOICES, blank=True, null=True)

    def __unicode__(self):
        return self.article.__unicode__()

    @property
    def _headline(self):
        return self.article.headline

    @property
    def homelead(self):
        return self.article.home_lead

    @property
    def _section(self):
        return self.article.sections.all()[:1].get()

    @property
    def _sections(self):
        return self.article.sections.all().get()

    @property
    def _slug(self):
        return self.article.slug

    @property
    def _deck(self):
        return self.article.deck

    @property
    def _body(self):
        return self.article.body

    @property
    def _byline(self):
        return self.article.byline

    @property
    def _date_published(self):
        return self.article.date_published

    @property
    def _allow_comments(self):
        return self.article.allow_comments

    @property
    def _photo(self):
        return self.article.photo

    @property
    def _gallery(self):
        return self.article.gallery

    @property
    def _video(self):
        return self.article.video

    def get_lead(self):
        if self.lead:
            return self.lead
        elif self.article.lead:
            return self.article.lead
        return ''

    def get_discussion_url(self):
        return self.article.get_discussion_url()

    def get_feed_url(self):
        return self.article.get_feed_url()

    def comment_count(self):
        return self.article.comment_count()

    def get_absolute_url(self):
        return self.article.get_absolute_url()

    def save(self):
        from core.utils import add_punctuation

        if not self.lead:
            if self.article.lead:
                self.lead = self.article.lead
        else:
            self.lead = self.lead.strip()
            self.lead = add_punctuation(self.lead)

        self.article.home_lead = self.lead
        self.article.home_display = self.display
        self.article.save()
        super(HomeArticle, self).save()

    class Meta:
        get_latest_by = 'article__date_published'
        ordering = ('-article__date_published', 'article__headline')
        verbose_name = u'artículo en portada'
        verbose_name_plural = u'artículos en portada'


class Module(Model):
    # TODO: add on_delete=SET_NULL for all articles
    home = ForeignKey(Home, unique=True, verbose_name=u'portada', related_name='modules')
    article_1 = ForeignKey(
        Article, null=True, blank=True, verbose_name=u'destacado 1', related_name='module_1', on_delete=SET_NULL)
    article_1_fixed = BooleanField('fijo')
    article_2 = ForeignKey(
        Article, null=True, blank=True, verbose_name=u'destacado 2', related_name='module_2', on_delete=SET_NULL)
    article_2_fixed = BooleanField('fijo')
    article_3 = ForeignKey(
        Article, null=True, blank=True, verbose_name=u'destacado 3', related_name='module_3', on_delete=SET_NULL)
    article_3_fixed = BooleanField('fijo')
    article_4 = ForeignKey(
        Article, null=True, blank=True, verbose_name=u'destacado 4', related_name='module_4', on_delete=SET_NULL)
    article_4_fixed = BooleanField('fijo')
    article_5 = ForeignKey(
        Article, null=True, blank=True, verbose_name=u'destacado 5', related_name='module_5', on_delete=SET_NULL)
    article_5_fixed = BooleanField('fijo')
    article_6 = ForeignKey(
        Article, null=True, blank=True, verbose_name=u'destacado 6', related_name='module_6', on_delete=SET_NULL)
    article_6_fixed = BooleanField('fijo')
    article_7 = ForeignKey(
        Article, null=True, blank=True, verbose_name=u'destacado 7', related_name='module_7', on_delete=SET_NULL)
    article_7_fixed = BooleanField('fijo')
    article_8 = ForeignKey(
        Article, null=True, blank=True, verbose_name=u'destacado 8', related_name='module_8', on_delete=SET_NULL)
    article_8_fixed = BooleanField('fijo')
    article_9 = ForeignKey(
        Article, null=True, blank=True, verbose_name=u'destacado 9', related_name='module_9', on_delete=SET_NULL)
    article_9_fixed = BooleanField('fijo')

    def __unicode__(self):
        count = self.count_articles()
        return u'%s - %d artículo%s' % (self.home, count, 's' if count > 1 else '')

    def count_articles(self):
        how_many = 0
        for x in range(1, 10):
            if getattr(self, 'article_%d' % x, None):
                how_many += 1
        return how_many

    def article_1_last_published(self):
        return self.article_1.last_published_by_category(self.home.category)
    article_1_last_published.short_description = u'last published'

    def article_2_last_published(self):
        return self.article_2.last_published_by_category(self.home.category)
    article_2_last_published.short_description = u'last published'

    def article_3_last_published(self):
        return self.article_3.last_published_by_category(self.home.category)
    article_3_last_published.short_description = u'last published'

    def article_4_last_published(self):
        return self.article_4.last_published_by_category(self.home.category)
    article_4_last_published.short_description = u'last published'

    def article_5_last_published(self):
        return self.article_5.last_published_by_category(self.home.category)
    article_5_last_published.short_description = u'last published'

    def article_6_last_published(self):
        return self.article_6.last_published_by_category(self.home.category)
    article_6_last_published.short_description = u'last published'

    def article_7_last_published(self):
        return self.article_7.last_published_by_category(self.home.category)
    article_7_last_published.short_description = u'last published'

    def article_8_last_published(self):
        return self.article_8.last_published_by_category(self.home.category)
    article_8_last_published.short_description = u'last published'

    def article_9_last_published(self):
        return self.article_9.last_published_by_category(self.home.category)
    article_9_last_published.short_description = u'last published'

    @property
    def articles_as_list(self):
        articles_ids = []
        for x in range(1, 10):
            a_id = getattr(self, 'article_%d_id' % x, None)
            if a_id:
                articles_ids.append(a_id)
        return [t[0] for t in sorted(
            ((a, articles_ids.index(a.id)) for a in Article.objects.filter(id__in=articles_ids)), key=itemgetter(1))]

    class Meta:
        verbose_name = u'destacados de área'
        app_label = 'core'
        ordering = ('home', )
