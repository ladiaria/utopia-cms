# -*- coding: utf-8 -*-
from datetime import date, timedelta
import requests
from requests.exceptions import ConnectionError

from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin import ModelAdmin, TabularInline, site
from django.forms import ModelForm, ValidationError, ChoiceField, RadioSelect
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.forms.fields import CharField, IntegerField
from django.forms.widgets import TextInput, HiddenInput
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django_markdown.widgets import MarkdownWidget

from actstream.models import Action

from tasks import update_category_home
from tagging.models import Tag, TaggedItem
from tagging.forms import TagField
from tagging_autocomplete_tagit.widgets import TagAutocompleteTagIt
from models import (
    Article,
    ArticleExtension,
    ArticleBodyImage,
    Edition,
    Journalist,
    Location,
    PrintOnlyArticle,
    Section,
    Supplement,
    Publication,
    ArticleRel,
    Category,
    CategoryHome,
    CategoryHomeArticle,
    ArticleUrlHistory,
    BreakingNewsModule,
)


class PrintOnlyArticleInline(TabularInline):
    model = PrintOnlyArticle
    extra = 10


class ArticleRelForm(ModelForm):

    class Meta:
        fields = ('article', 'top_position')
        model = ArticleRel


class TopArticleRelBaseInlineFormSet(BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        super(TopArticleRelBaseInlineFormSet, self).__init__(*args, **kwargs)
        self.can_delete = False


TopArticleRelInlineFormSet = inlineformset_factory(
    Edition, ArticleRel, form=ArticleRelForm, formset=TopArticleRelBaseInlineFormSet
)


class HomeTopArticleInline(TabularInline):
    model = ArticleRel
    extra = 0
    max_num = 0
    ordering = ('top_position', )
    fields = ('article', 'section', 'top_position')
    readonly_fields = ('section', )
    raw_id_fields = ('article', )
    verbose_name_plural = u'Nota de tapa y titulines'
    formset = TopArticleRelInlineFormSet

    def get_queryset(self, request):
        qs = super(HomeTopArticleInline, self).get_queryset(request)
        return qs.filter(home_top=True)

    class Media:
        # jquery loaded again (admin uses custom js namespaces)
        js = (
            'admin/js/jquery%s.js' % ('' if settings.DEBUG else '.min'),
            'js/jquery-ui-1.12.1.custom.min.js',
            'js/homev2/edition_admin.js',
        )
        css = {'all': ('css/home_admin.css', )}


class SectionArticleRelForm(ModelForm):

    class Meta:
        fields = ('article', 'position', 'home_top')
        model = ArticleRel


SectionArticleRelInlineFormSet = inlineformset_factory(Edition, ArticleRel, form=SectionArticleRelForm)


def section_top_article_inline_class(section):

    class SectionTopArticleInline(HomeTopArticleInline):
        max_num = 20
        verbose_name_plural = u'Artículos en %s [[%d]]' % (section.name, section.id)
        fields = ('article', 'position', 'home_top')
        raw_id_fields = ('article', )
        ordering = ('position', )
        formset = SectionArticleRelInlineFormSet

        def get_queryset(self, request):
            # calling super of HomeTopArticleInline to avoid top=true filter
            qs = super(HomeTopArticleInline, self).get_queryset(request)
            return qs.filter(section=section)

    return SectionTopArticleInline


class EditionAdmin(ModelAdmin):
    fields = ('date_published', 'pdf', 'cover', 'publication')
    list_display = ('edition_pub', 'title', 'pdf', 'cover', 'get_supplements')
    list_filter = ('date_published', 'publication')
    search_fields = ('title', )
    date_hierarchy = 'date_published'
    publication = None

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            self.publication = obj.publication
        return super(EditionAdmin, self).get_form(request, obj, **kwargs)

    def get_inline_instances(self, request, obj=None):
        self.inlines = [HomeTopArticleInline]
        if self.publication:
            for section in self.publication.section_set.order_by('home_order'):
                self.inlines.append(section_top_article_inline_class(section))
        return super(EditionAdmin, self).get_inline_instances(request)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'cover':
            kwargs['queryset'] = self.articles_qs
            return db_field.formfield(**kwargs)
        return super(EditionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_urls(self):
        urls = super(EditionAdmin, self).get_urls()
        my_urls = [
            url(
                r'^add_article/(?P<ed_id>\d+)/(?P<sec_id>\d+)/(?P<art_id>\d+)/$',
                self.admin_site.admin_view(self.add_article),
            ),
        ]
        return my_urls + urls

    def add_article(self, request, ed_id, sec_id, art_id):
        edition = get_object_or_404(Edition, pk=ed_id)
        section = get_object_or_404(Section, pk=sec_id)
        article = get_object_or_404(Article, pk=art_id)
        ArticleRel.objects.create(edition=edition, section=section, article=article)
        return HttpResponseRedirect("/admin/core/edition/" + ed_id)

    def save_related(self, request, form, formsets, change):
        super(EditionAdmin, self).save_related(request, form, formsets, change)
        update_category_home()


class PortableDocumentFormatPageAdmin(ModelAdmin):
    pass


class SectionAdminModelForm(ModelForm):
    # It uses the same tags than articles. (TODO: explain better this comment)
    tags = TagField(widget=TagAutocompleteTagIt({'app': 'core', 'model': 'article'}), required=False)

    class Meta:
        model = Section
        fields = "__all__"


class SectionAdmin(ModelAdmin):
    list_editable = ('name', 'home_order', 'in_home')
    list_filter = ('category', 'in_home', 'home_block_all_pubs', 'home_block_show_featured')
    list_display = (
        'id',
        'name',
        'category',
        'in_home',
        'home_order',
        'get_publications',
        'articles_count',
    )
    search_fields = ('name', 'name_in_category_menu', 'contact')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('name', 'category', 'name_in_category_menu'),
                    ('description', 'show_description'),
                    ('home_order', 'white_text', 'background_color'),
                    ('publications', ),
                    ('in_home', ),
                    ('home_block_all_pubs', ),
                    ('home_block_show_featured', ),
                    ('imagen', 'show_image', 'contact'),
                ),
            },
        ),
    )

    def save_related(self, request, form, formsets, change):
        super(SectionAdmin, self).save_related(request, form, formsets, change)
        update_category_home()


class ArticleExtensionInline(TabularInline):
    model = ArticleExtension
    extra = 1


class ArticleBodyImageInline(TabularInline):
    model = ArticleBodyImage
    extra = 0
    raw_id_fields = ('image', )
    readonly_fields = ['photo_admin_thumbnail', 'photo_date_taken', 'photo_date_added']

    def photo_admin_thumbnail(self, instance):
        return instance.image.admin_thumbnail()
    photo_admin_thumbnail.short_description = u'thumbnail'
    photo_admin_thumbnail.allow_tags = True

    def photo_date_taken(self, instance):
        return instance.image.date_taken
    photo_date_taken.short_description = u'tomada el'

    def photo_date_added(self, instance):
        return instance.image.date_added
    photo_date_added.short_description = u'fecha de creación'


class ArticleRelAdminModelForm(ModelForm):
    main = ChoiceField(label=u'principal', widget=RadioSelect, choices=((1, u''), ), required=False)

    class Meta:
        model = ArticleRel
        fields = "__all__"


class ArticleEditionInline(TabularInline):
    verbose_name = verbose_name_plural = u'publicado en'
    model = ArticleRel
    raw_id_fields = ('edition', )
    form = ArticleRelAdminModelForm
    extra = 1


class ArticleAdminModelForm(ModelForm):
    body = CharField(widget=MarkdownWidget())
    headline = CharField(label='Título', widget=TextInput(attrs={'style': 'width:600px'}))
    tags = TagField(widget=TagAutocompleteTagIt(max_tags=False), required=False)

    def clean_tags(self):
        """
        This is a hack to bypass the bug that: 1 tag with spaces is considered as many tags by the lib.
        This doesn't ocurr with 2 tags or more.
        With double quotes, the tag with spaces is correctly interpreted.
        """
        tags = self.cleaned_data.get('tags')
        if tags and ',' not in tags:
            # there is just 1 tag
            tags = tags.strip('"')
            tags = '"' + tags + '"'
        return tags

    class Meta:
        model = Article
        fields = "__all__"


def has_photo(obj):
    return bool(obj.photo is not None)


has_photo.short_description = u'Foto'
has_photo.boolean = True


def has_gallery(obj):
    return bool(obj.gallery is not None)


has_gallery.short_description = u'Galería'
has_gallery.boolean = True

article_optional_inlines = []

if 'core.attachments' in settings.INSTALLED_APPS:
    from core.attachments.models import Attachment

    class AttachmentInline(TabularInline):
        model = Attachment
        extra = 1

    article_optional_inlines.append(AttachmentInline)


def get_editions():
    since = date.today() - timedelta(days=5)
    return Edition.objects.filter(date_published__gte=since)


class ArticleAdmin(ModelAdmin):
    # TODO: Do not allow delete if the article is the main article in a category home (home.models.Home)
    form = ArticleAdminModelForm
    prepopulated_fields = {'slug': ('headline',)}
    filter_horizontal = ('byline',)
    list_display = (
        'headline', 'type', 'get_publications', 'get_sections', 'date_published', 'is_published', has_photo, 'surl'
    )
    list_select_related = True
    list_filter = ('type', 'date_created', 'is_published', 'date_published', 'newsletter_featured', 'byline')
    search_fields = ['headline', 'slug', 'deck', 'lead', 'body']
    date_hierarchy = 'date_published'
    raw_id_fields = ('photo', 'gallery', 'main_section')
    inlines = article_optional_inlines + [ArticleExtensionInline, ArticleBodyImageInline, ArticleEditionInline]

    fieldsets = (
        (None, {'fields': ('type', 'headline', 'keywords', 'deck', 'lead', 'body'), 'classes': ('wide', )}),
        (
            'Portada',
            {
                'fields': ('home_lead', 'home_top_deck', 'home_display', 'home_header_display', 'header_display'),
                'classes': ('wide', ),
            }
        ),
        ('Metadatos', {'fields': ('date_published', 'tags', 'main_section')}),
        ('Autor', {'fields': ('byline', 'only_initials', 'location'), 'classes': ('collapse', )}),
        ('Multimedia', {'fields': ('photo', 'gallery', 'video', 'youtube_video', 'audio'), 'classes': ('collapse', )}),
        (
            'Avanzado',
            {
                'fields': (
                    'slug',
                    'allow_comments',
                    'is_published',
                    'public',
                    'allow_related',
                    'show_related_articles',
                    'newsletter_featured',
                    'latitude',
                    'longitude',
                ),
                'classes': ('collapse', ),
            },
        ),
    )

    def get_object(self, request, object_id, from_field=None):
        # Hook obj for use in formfield_for_manytomany
        self.obj = super(ArticleAdmin, self).get_object(request, object_id)
        if not self.obj:
            raise Http404
        # Save old url_path to be used in save_related
        self.old_url_path = self.obj.url_path
        return self.obj

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # TODO: publication field will be removed from database, update this code or remove this method if no necessary
        if db_field.name == "sections":
            if 'publication' in request.GET:
                publication_id = request.GET['publication']
                publication = Publication.objects.filter(id=publication_id)
            elif getattr(self, 'obj', None):
                publication = self.obj.publication
            else:
                publication = None
            kwargs["queryset"] = publication.section_set.all()
        return super(ArticleAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'publication':
            return db_field.formfield(**kwargs)
        return super(ArticleAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if form.is_valid():
            try:
                super(ArticleAdmin, self).save_model(request, obj, form, change)
                self.obj = obj
            except Exception as e:
                # TODO: how this print can help? review this ASAP
                print(e)

    def save_related(self, request, form, formsets, change):
        super(ArticleAdmin, self).save_related(request, form, formsets, change)

        # main "main" section radiobutton in inline (also has js hacks) mapped to main_section attribute:
        save = False
        # TODO: message_user is not working in development env
        if not self.obj.sections.exists():
            if self.obj.main_section:
                self.obj.main_section, save = None, True
                self.message_user(request, u'AVISO: Ninguna publicación definida como principal')
        elif self.obj.sections.count() == 1:
            # If only one "published in" row => set it as main (if different)
            main_section = ArticleRel.objects.get(article=self.obj)
            if self.obj.main_section != main_section:
                self.obj.main_section, save = main_section, True
                self.message_user(request, u'Publicación principal: %s' % main_section)
        else:
            row_selected = request.POST.get('main_section_radio')
            if row_selected:
                if request.POST.get('articlerel_set-%s-DELETE' % row_selected) != u'on':
                    # a kept or new row was selected as "main" => set it as the main_section (if different)
                    articlerel_id = request.POST.get('articlerel_set-%s-id' % row_selected)
                    if articlerel_id:
                        if self.obj.main_section_id != articlerel_id:
                            self.obj.main_section_id, save = articlerel_id, True
                            self.message_user(request, u'Publicación principal: %s' % self.obj.main_section)
                    else:
                        main_section = ArticleRel.objects.get(
                            article=self.obj, edition=request.POST.get('articlerel_set-%s-edition' % row_selected),
                            section=request.POST.get('articlerel_set-%s-section' % row_selected))
                        if self.obj.main_section != main_section:
                            self.obj.main_section, save = main_section, True
                            self.message_user(request, u'Publicación principal: %s' % main_section)
            else:
                # no row was selected, set the oldest as the main_section (if different)
                main_section = ArticleRel.objects.filter(article=self.obj).order_by('edition__date_published')[0]
                if self.obj.main_section != main_section:
                    self.obj.main_section, save = main_section, True
                    self.message_user(request, u'Publicación principal: %s' % main_section)

        if save:
            self.obj.save()

        if change:
            # need refresh from db
            self.obj = Article.objects.get(id=self.obj.id)
        new_url_path = self.obj.build_url_path()
        url_changed = getattr(self, 'old_url_path', u'') != new_url_path
        if url_changed:
            self.obj.url_path = new_url_path
            self.obj.save()

            talk_url = getattr(settings, 'TALK_URL', None)
            if change and talk_url and not settings.DEBUG:
                # the article has a new url, we need to update it in Coral-Talk using the API
                # but don't do this in DEBUG mode to avoid updates with local urls in Coral
                # TODO: do not message user if the story is not found in coral (use "code" value in response.errors)
                try:
                    requests.post(
                        talk_url + 'api/graphql',
                        headers={
                            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + settings.TALK_API_TOKEN
                        },
                        data='{"operationName":"updateStory","variables":{"input":{"id":%d,"story":{"url":"%s://%s%s"}'
                        ',"clientMutationId":"url updated"}},"query":"mutation updateStory($input: UpdateStoryInput!)'
                        '{updateStory(input:$input){story{id}}}"}' % (
                            form.instance.id, settings.URL_SCHEME, settings.SITE_DOMAIN, new_url_path)
                    ).json()['data']['updateStory']['story']
                except (ConnectionError, ValueError, KeyError, AssertionError, TypeError):
                    self.message_user(request, u'AVISO: No se pudo actualizar la nueva URL en Coral-Talk')

        # add to history the new url
        if not ArticleUrlHistory.objects.filter(article=form.instance, absolute_url=new_url_path).exists():
            ArticleUrlHistory.objects.create(article=form.instance, absolute_url=new_url_path)

        update_category_home()

    def changelist_view(self, request, extra_context=None):
        if 'type__exact' not in request.GET:
            q = request.GET.copy()
            q['type__exact'] = 'NE'  # Setea el filtro por defecto a noticias
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(ArticleAdmin, self).changelist_view(
            request, extra_context=extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        # actstream does not return unicode when rendering an Action if the target object has non-ascii chars,
        # this breaks the django six names collector, and this temporal change can hack this when deleting an article.
        Action.__unicode__ = lambda x: u'Article followed by user'
        response = super(ArticleAdmin, self).delete_view(request, object_id, extra_context)
        del Action.__unicode__
        return response

    class Media:
        css = {'all': ('css/charcounter.css', 'css/admin_article.css')}
        # jquery loaded again (admin uses custom js namespaces)
        js = (
            'admin/js/jquery%s.js' % ('' if settings.DEBUG else '.min'),
            'js/jquery.charcounter-orig.js',
            'js/markdown-help.js',
            'js/homev2/article_admin.js',
        )


class SupplementAdmin(ModelAdmin):
    fieldsets = ((None, {'fields': ('edition', 'name', 'headline', 'pdf', 'public')}), )
    date_hierarchy = 'date_published'
    list_display = ('name', 'edition', 'date_published', 'pdf', 'cover', 'public')
    list_filter = ('name', 'date_created', 'public')
    search_fields = ['name', 'date_published']
    raw_id_fields = ['edition']


class PrintOnlyArticleAdmin(ModelAdmin):
    list_display = ('headline', 'deck', 'edition')
    list_filter = ('date_created',)
    search_fields = ['headline', 'deck']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'edition':
            kwargs['queryset'] = get_editions()
            return db_field.formfield(**kwargs)
        return super(ArticleAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)


def published_articles(obj):
    return obj.articles_core.filter(is_published=True).count()


published_articles.short_description = 'Artículos publicados'


class JournalistForm(ModelForm):
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if name.isnumeric():
            raise ValidationError(u'El nombre no puede ser un número.')
        else:
            return name

    class Meta:
        model = Journalist
        fields = '__all__'


class JournalistAdmin(ModelAdmin):
    form = JournalistForm
    list_display = ('name', 'job', published_articles)
    list_filter = ('job',)
    search_fields = ['name']
    fieldsets = (
        (None, {'fields': ('name', 'email', 'image', 'bio', 'job', 'sections')}),
        (
            'Redes sociales',
            {'description': 'Ingrese nombre de usuario de cada red social.', 'fields': ('fb', 'tt', 'gp', 'ig')},
        ),
    )


class LocationAdmin(ModelAdmin):
    pass


class PublicationAdminChangelistForm(ModelForm):
    name = CharField(widget=TextInput(attrs={'size': 15}))
    headline = CharField(widget=TextInput(attrs={'size': 25}))

    class Meta:
        model = Publication
        fields = ('name', 'headline', 'weight', 'public', 'has_newsletter')


class PublicationAdmin(ModelAdmin):
    list_display = (
        'id',
        'name',
        'slug',
        'headline',
        'weight',
        'public',
        'has_newsletter',
        'subscriber_count',
        'image_tag',
        'get_full_width_cover_image_tag',
    )
    list_editable = ('name', 'headline', 'weight', 'public', 'has_newsletter')
    raw_id_fields = ('full_width_cover_image', )

    def get_changelist_form(self, request, **kwargs):
        kwargs.setdefault('form', PublicationAdminChangelistForm)
        return super(PublicationAdmin, self).get_changelist_form(request, **kwargs)


class CategoryAdmin(ModelAdmin):
    list_display = (
        'id', 'name', 'order', 'slug', 'title', 'has_newsletter', 'subscriber_count', 'get_full_width_cover_image_tag'
    )
    list_editable = ('name', 'order', 'slug', 'has_newsletter')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('name', 'slug', 'order'),
                    ('exclude_from_top_menu', ),
                    ('title', 'more_link_title', 'new_pill'),
                    ('description', ),
                    ('full_width_cover_image', 'full_width_cover_image_title'),
                    ('full_width_cover_image_lead', ),
                    ('has_newsletter', 'newsletter_tagline', 'newsletter_periodicity'),
                    ('subscribe_box_question', ),
                    ('subscribe_box_nl_subscribe_auth', ),
                    ('subscribe_box_nl_subscribe_anon', ),
                ),
            },
        ),
    )
    raw_id_fields = ('full_width_cover_image', )


class CategoryHomeArticleForm(ModelForm):
    pos = IntegerField(label='orden', widget=TextInput(attrs={'size': 5, 'readonly': True}))

    class Meta:
        fields = ['position', 'pos', 'home', 'article', 'fixed']
        model = CategoryHomeArticle


CategoryHomeArticleFormSetBase = inlineformset_factory(CategoryHome, CategoryHomeArticle, form=CategoryHomeArticleForm)


class CategoryHomeArticleFormSet(CategoryHomeArticleFormSetBase):

    def add_fields(self, form, index):
        super(CategoryHomeArticleFormSet, self).add_fields(form, index)
        form.fields["position"].widget = HiddenInput()
        if index is not None:
            form.fields["pos"].initial = index + 1
            form.fields["position"].initial = index + 1


class CategoryHomeArticleInline(TabularInline):
    model = CategoryHome.articles.through
    extra = 20
    max_num = 20
    form = CategoryHomeArticleForm
    formset = CategoryHomeArticleFormSet
    raw_id_fields = ('article', )
    verbose_name_plural = u'Artículos en portada'


class CategoryHomeAdmin(admin.ModelAdmin):
    list_display = ('category', )
    exclude = ('articles', )
    inlines = [CategoryHomeArticleInline]


class ArticleInline(TabularInline):
    model = BreakingNewsModule.articles.through
    extra = 3
    max_num = 3
    raw_id_fields = ('article', )
    verbose_name_plural = u'Artículos relacionados'


class BreakingNewsModuleAdmin(ModelAdmin):
    list_display = ('id', 'headline', 'deck', 'covers', 'is_published')
    list_editable = ('headline', 'deck', 'is_published')
    list_filter = ('is_published', 'publications', 'categories')
    exclude = ('articles', )
    inlines = [ArticleInline]
    fieldsets = (
        (None, {'fields': (('is_published', 'headline', 'deck'), )}),
        ('Portadas', {'fields': (('publications', 'categories'), )}),
        ('Notificación', {'fields': (('enable_notification', 'notification_url'), ('notification_text'))}),
        (
            'Bloques incrustados',
            {
                'fields': (
                    ('embeds_headline', 'embeds_description'),
                    ('embed1_title', 'embed1_content'),
                    ('embed2_title', 'embed2_content'),
                    ('embed3_title', 'embed3_content'),
                    ('embed4_title', 'embed4_content'),
                    ('embed5_title', 'embed5_content'),
                    ('embed6_title', 'embed6_content'),
                    ('embed7_title', 'embed7_content'),
                    ('embed8_title', 'embed8_content'),
                    ('embed9_title', 'embed9_content'),
                    ('embed10_title', 'embed10_content'),
                    ('embed11_title', 'embed11_content'),
                    ('embed12_title', 'embed12_content'),
                    ('embed13_title', 'embed13_content'),
                    ('embed14_title', 'embed14_content'),
                ),
            },
        ),
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super(BreakingNewsModuleAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name in ('deck', 'embeds_description', 'notification_text'):
            field.widget.attrs['style'] = 'width:50em;'
        elif db_field.name in ('publications', 'categories'):
            field.widget.attrs['size'] = max((Publication.objects.count(), Category.objects.count()))
        return field

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "articles":
            kwargs["queryset"] = Article.objects.filter(is_published=True)
        return super(BreakingNewsModuleAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


class TagAdmin(admin.ModelAdmin):
    model = Tag
    search_fields = ('name',)


class TaggedItemAdmin(admin.ModelAdmin):
    model = TaggedItem
    search_fields = ('name',)


site.register(Article, ArticleAdmin)
site.register(Edition, EditionAdmin)
site.register(Journalist, JournalistAdmin)
site.register(Location, LocationAdmin)
site.register(PrintOnlyArticle, PrintOnlyArticleAdmin)
site.register(Section, SectionAdmin)
site.register(Supplement, SupplementAdmin)
site.register(Publication, PublicationAdmin)
site.register(Category, CategoryAdmin)
site.register(CategoryHome, CategoryHomeAdmin)
site.register(BreakingNewsModule, BreakingNewsModuleAdmin)
site.unregister(Tag)
site.unregister(TaggedItem)
site.register(Tag, TagAdmin)
site.register(TaggedItem, TaggedItemAdmin)
