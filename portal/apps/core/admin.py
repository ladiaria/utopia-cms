# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from datetime import date, timedelta
from requests.exceptions import ConnectionError
import json
from urllib.parse import urljoin
from pydoc import locate

from django_markdown.widgets import MarkdownWidget
from actstream.models import Action
from tagging.models import Tag, TaggedItem
from tagging.forms import TagField
from tagging_autocomplete_tagit.widgets import TagAutocompleteTagIt

from django.conf import settings
from django.conf.urls import url
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.messages import constants as messages
from django.contrib.admin import ModelAdmin, TabularInline, site, widgets
from django.contrib.admin.options import get_ul_class
from django.forms import (
    ModelForm, ValidationError, ChoiceField, RadioSelect, TypedChoiceField, Field, Textarea, Widget
)
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone
from django.forms.fields import CharField, IntegerField
from django.forms.widgets import TextInput, HiddenInput
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.text import Truncator
from django.utils.translation import ugettext as _

from django.template import loader
from django.utils.safestring import mark_safe

from core.templatetags.ldml import ldmarkup, cleanhtml

from .models import (
    Article,
    ArticleExtension,
    ArticleBodyImage,
    Edition,
    EditionHeader,
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
    CategoryNewsletter,
    CategoryNewsletterArticle,
    ArticleUrlHistory,
    BreakingNewsModule,
    DeviceSubscribed,
    PushNotification,
)
from .tasks import update_category_home, send_push_notification
from .utils import update_article_url_in_coral_talk, smart_quotes


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
    verbose_name_plural = 'Nota de tapa y titulines'
    formset = TopArticleRelInlineFormSet
    classes = ('dynamic-order',)

    def get_queryset(self, request):
        qs = super(HomeTopArticleInline, self).get_queryset(request)
        return qs.filter(home_top=True)

    class Media:
        # jquery loaded again (admin uses custom js namespaces)
        js = (
            'admin/js/jquery%s.js' % ('' if settings.DEBUG else '.min'),
            'js/jquery-ui-1.12.1.custom.min.js',
            'js/homev2/dynamic_edition_admin.js',
            'js/RelatedObjectLookupsCustom.js',
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
        verbose_name_plural = 'Artículos en %s [[%d]]' % (section.name, section.id)
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
    # TODO: use this form to validate for ex. when a Section cannot be saved (dupe slug or anything)

    class Meta:
        fields = "__all__"
        widgets = {'html_title': TextInput(attrs={'size': 128}), 'meta_description': Textarea()}


class SectionAdmin(ModelAdmin):
    form = SectionAdminModelForm
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
        ('Metadatos', {'fields': (('html_title', ), ('meta_description', ))}),
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
    photo_admin_thumbnail.short_description = 'thumbnail'
    photo_admin_thumbnail.allow_tags = True

    def photo_date_taken(self, instance):
        return instance.image.date_taken
    photo_date_taken.short_description = 'tomada el'

    def photo_date_added(self, instance):
        return instance.image.date_added
    photo_date_added.short_description = 'fecha de creación'


class ArticleRelAdminModelForm(ModelForm):
    main = ChoiceField(label='principal', widget=RadioSelect, choices=((1, ''), ), required=False)

    class Meta:
        model = ArticleRel
        fields = "__all__"


class ArticleEditionInline(TabularInline):
    verbose_name = verbose_name_plural = 'publicado en'
    model = ArticleRel
    raw_id_fields = ('edition', )
    form = ArticleRelAdminModelForm
    extra = 1


class SolanaSignatureWidget(Widget):
    template_name = 'admin/core/article/solana_signature.html'

    def __init__(self, *args, **kwargs):
        kwargs['attrs'] = {'readonly': True}
        super(SolanaSignatureWidget, self).__init__(*args, **kwargs)

    def get_context(self, name, value, attrs=None):
        return {'widget': {
            'name': name,
            'value': value,
        }}

    def render(self, name, value, attrs=None):
        context = self.get_context(name, value, attrs)
        template = loader.get_template(self.template_name).render(context)
        return mark_safe(template)

class SolanaSignatureField(Field):
    def __init__(self, field, *args, **kwargs):
        self.field = field
        kwargs["widget"] = SolanaSignatureWidget

        super(SolanaSignatureField, self).__init__(*args, **kwargs)

    def clean(self, value):
        return value

class ArticleAdminModelForm(ModelForm):
    body = CharField(widget=MarkdownWidget())
    solana_signature_address = SolanaSignatureField(
        "Firma con Solana",
        label='Firma con Solana',
        required=False,
        help_text=(
            'Podés firmar esta nota con Solana desde tu wallet. '
            '<a href="https://solana.com/" target="_blank">¿Qué es Solana?</a>'
        ),
    )
    headline = CharField(label='Título', widget=TextInput(attrs={'style': 'width:600px'}))
    slug = CharField(
        label='Slug',
        widget=TextInput(attrs={'style': 'width:600px', 'readonly': 'readonly'}),
        help_text='Se genera automáticamente en base al título.',
    )
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

    def clean(self):
        cleaned_data = super(ArticleAdminModelForm, self).clean()
        date_value = (
            self.cleaned_data.get('date_published') if self.cleaned_data.get('is_published') else
            self.cleaned_data.get('date_created')
        ) or date.today()
        targets = Article.objects.filter(
            Q(is_published=True) & Q(date_published__year=date_value.year) & Q(date_published__month=date_value.month)
            | Q(is_published=False) & Q(date_created__year=date_value.year) & Q(date_created__month=date_value.month),
            slug=slugify(cleanhtml(ldmarkup(smart_quotes(cleaned_data.get('headline'))))),
        )
        if self.instance.id:
            targets = targets.exclude(id=self.instance.id)
        if targets:
            raise ValidationError('Ya existe un artículo en ese mes con el mismo título.')

    class Meta:
        model = Article
        fields = "__all__"


def has_photo(obj):
    return bool(obj.photo is not None)


has_photo.short_description = 'Foto'
has_photo.boolean = True


def has_gallery(obj):
    return bool(obj.gallery is not None)


has_gallery.short_description = 'Galería'
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

    prepopulated_fields = {'slug': ('headline', )}
    filter_horizontal = ('byline', )
    list_display = (
        'id',
        'headline',
        'type',
        'get_publications',
        'get_sections',
        'creation_date',
        'publication_date',
        'is_published',
        has_photo,
        'surl',
    )
    list_select_related = True
    list_filter = ('type', 'date_created', 'is_published', 'date_published', 'newsletter_featured', 'byline')
    search_fields = ['headline', 'slug', 'deck', 'lead', 'body']
    date_hierarchy = 'date_published'
    ordering = ('-date_created', )
    raw_id_fields = ('photo', 'gallery', 'main_section')
    readonly_fields = ('date_published', 'solana_signature')
    inlines = article_optional_inlines + [ArticleExtensionInline, ArticleBodyImageInline, ArticleEditionInline]

    def creation_date(self, obj):
        return obj.date_created.strftime("%d %b %Y %H:%M")
    creation_date.admin_order_field = 'date_created'
    creation_date.short_description = 'Creado'

    def publication_date(self, obj):
        if obj.date_published:
            return obj.date_published.strftime("%d %b %Y %H:%M")
        else:
            return ''
    publication_date.admin_order_field = 'date_published'
    publication_date.short_description = 'Publicado'

    fieldsets = (
        (None, {'fields': ('type', 'headline', 'slug', 'keywords', 'deck', 'lead', 'body'), 'classes': ('wide', )}),
        (
            'Portada',
            {
                'fields': ('home_lead', 'home_top_deck', 'home_display', 'home_header_display', 'header_display'),
                'classes': ('wide', ),
            }
        ),
        ('Metadatos', {'fields': ('date_published', 'tags', 'main_section')}),
        ('Autor', {'fields': ('byline', 'only_initials', 'location', 'solana_signature_address'), 'classes': ('collapse', )}),
        ('Multimedia', {'fields': ('photo', 'gallery', 'video', 'youtube_video', 'audio'), 'classes': ('collapse', )}),
        (
            'Avanzado',
            {
                'fields': (
                    (
                        'allow_comments',
                        'is_published',
                        'public',
                        'allow_related',
                        'show_related_articles',
                        'newsletter_featured',
                        'ipfs_upload',
                    ),
                    'additional_access',
                    ('latitude', 'longitude'),
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
                obj.admin = True  # tell model's save method that we are calling it from the admin
                super(ArticleAdmin, self).save_model(request, obj, form, change)
                self.obj = obj
            except Exception as e:
                if settings.DEBUG:
                    print(e)

    def save_related(self, request, form, formsets, change):
        super(ArticleAdmin, self).save_related(request, form, formsets, change)

        # main "main" section radiobutton in inline (also has js hacks) mapped to main_section attribute:
        save = False
        # TODO: message_user is not working in development env
        if not self.obj.sections.exists():
            if self.obj.main_section:
                self.obj.main_section, save = None, True
                self.message_user(request, 'AVISO: Ninguna publicación definida como principal')
        elif self.obj.sections.count() == 1:
            # If only one "published in" row => set it as main (if different)
            main_section = ArticleRel.objects.get(article=self.obj)
            if self.obj.main_section != main_section:
                self.obj.main_section, save = main_section, True
                self.message_user(request, 'Publicación principal: %s' % main_section)
        else:
            row_selected = request.POST.get('main_section_radio')
            if row_selected:
                if request.POST.get('articlerel_set-%s-DELETE' % row_selected) != 'on':
                    # a kept or new row was selected as "main" => set it as the main_section (if different)
                    articlerel_id = request.POST.get('articlerel_set-%s-id' % row_selected)
                    if articlerel_id:
                        if self.obj.main_section_id != articlerel_id:
                            self.obj.main_section_id, save = articlerel_id, True
                            self.message_user(request, 'Publicación principal: %s' % self.obj.main_section)
                    else:
                        main_section = ArticleRel.objects.get(
                            article=self.obj,
                            edition=request.POST.get('articlerel_set-%s-edition' % row_selected),
                            section=request.POST.get('articlerel_set-%s-section' % row_selected),
                            position=request.POST.get('articlerel_set-%s-position' % row_selected),
                        )
                        if self.obj.main_section != main_section:
                            self.obj.main_section, save = main_section, True
                            self.message_user(request, 'Publicación principal: %s' % main_section)
            else:
                # no row was selected, set the oldest as the main_section (if different)
                main_section = ArticleRel.objects.filter(article=self.obj).order_by('edition__date_published')[0]
                if self.obj.main_section != main_section:
                    self.obj.main_section, save = main_section, True
                    self.message_user(request, 'Publicación principal: %s' % main_section)

        if save:
            self.obj.save()

        if change:
            # need refresh from db
            self.obj = Article.objects.get(id=self.obj.id)

        new_url_path = self.obj.build_url_path()
        url_changed = getattr(self, 'old_url_path', '') != new_url_path
        if url_changed:
            self.obj.url_path = new_url_path
            self.obj.save()

            talk_url = getattr(settings, 'TALK_URL', None)
            if change and talk_url and not settings.DEBUG:
                # the article has a new url, we need to update it in Coral-Talk using the API
                # but don't do this in DEBUG mode to avoid updates with local urls in Coral
                # TODO: do not message user if the story is not found in coral (use "code" value in response.errors)
                try:
                    update_article_url_in_coral_talk(form.instance.id, new_url_path)
                except (ConnectionError, ValueError, KeyError, AssertionError, TypeError):
                    self.message_user(request, 'AVISO: No se pudo actualizar la nueva URL en Coral-Talk')

        # add to history the new url
        if not ArticleUrlHistory.objects.filter(article=form.instance, absolute_url=new_url_path).exists():
            ArticleUrlHistory.objects.create(article=form.instance, absolute_url=new_url_path)

        # TODO: check if code below may be called also from the model save method
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
        # TODO: check if this issue is still present in py3
        Action.__str__ = lambda x: 'Article followed by user'
        response = super(ArticleAdmin, self).delete_view(request, object_id, extra_context)
        del Action.__str__
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


class EditionHeaderAdmin(ModelAdmin):
    list_display = ('edition', 'title', 'subtitle')
    fieldsets = ((None, {'fields': list_display}), )
    search_fields = list_editable = ['title', 'subtitle']
    raw_id_fields = ['edition']


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
            raise ValidationError('El nombre no puede ser un número.')
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


class CustomSubjectAdminForm(ModelForm):
    newsletter_automatic_subject = TypedChoiceField(
        label='',
        coerce=lambda x: x == 'True',
        choices=((True, 'Asunto automático'), (False, 'Asunto manual')),
        widget=RadioSelect,
    )

    def clean(self):
        cleaned_data = super(CustomSubjectAdminForm, self).clean()
        if cleaned_data.get('newsletter_automatic_subject') is False and not cleaned_data.get('newsletter_subject'):
            raise ValidationError('Se debe incluir un asunto de newsletter al configurarlo como "manual".')


class PublicationAdminForm(CustomSubjectAdminForm):

    class Meta:
        model = Publication
        fields = "__all__"
        widgets = {
            'newsletter_tagline': TextInput(attrs={'size': 160}),
            'newsletter_subject': TextInput(attrs={'size': 160}),
            'html_title': TextInput(attrs={'size': 128}),
            'meta_description': Textarea(),
        }


class PublicationAdmin(ModelAdmin):
    form = PublicationAdminForm
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
    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('name', 'image'),
                    ('twitter_username', ),
                    ('description', ),
                    ('slug', 'headline', 'weight'),
                    ('public', 'has_newsletter'),
                    ('newsletter_name', 'newsletter_logo'),
                    ('newsletter_tagline', ),
                    ('newsletter_periodicity', 'newsletter_header_color'),
                    ('newsletter_campaign', 'subscribe_box_question'),
                    ('subscribe_box_nl_subscribe_auth', 'subscribe_box_nl_subscribe_anon'),
                    ('full_width_cover_image', ),
                    ('is_emergente', 'new_pill'),
                ),
            },
        ),
        ('Asunto de newsletter', {'fields': (('newsletter_automatic_subject', ), ('newsletter_subject', ))}),
        (
            'Metadatos',
            {
                'fields': (
                    ('html_title', ),
                    ('meta_description', ),
                    ('icon', 'icon_png'),
                    ('icon_png_16', 'icon_png_32'),
                    ('apple_touch_icon_180', ),
                    ('apple_touch_icon_192', ),
                    ('apple_touch_icon_512', ),
                    ('open_graph_image', ),
                    ('open_graph_image_width', 'open_graph_image_height'),
                    ('publisher_logo', ),
                    ('publisher_logo_width', 'publisher_logo_height'),
                ),
            },
        ),
    )
    actions = ['send_newsletter']

    def get_changelist_form(self, request, **kwargs):
        kwargs.setdefault('form', PublicationAdminChangelistForm)
        return super(PublicationAdmin, self).get_changelist_form(request, **kwargs)

    def send_newsletter(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(
                request,
                "No se permite enviar más de un newsletter a la vez, seleccione solamente una publicación",
                level=messages.ERROR,
            )
        else:
            function_fullpath = getattr(settings, "CORE_PUBLICATIONS_NL_TASK", None)
            if function_fullpath:
                result_err = locate(function_fullpath)(queryset.first().slug)
                if result_err:
                    self.message_user(request, result_err, level=messages.ERROR)
                else:
                    self.message_user(
                        request,
                        "Comenzando el proceso de envío de la newsletter para la publicación seleccionada",
                        level=messages.SUCCESS,
                    )
            else:
                self.message_user(
                    request,
                    "No es posible realizar el envío, la tarea para el envío de newsletters no está configurada",
                    level=messages.ERROR,
                )
    send_newsletter.short_description = "Enviar el newsletter de la publicación seleccionada"


class CategoryAdminForm(CustomSubjectAdminForm):

    class Meta:
        model = Category
        fields = "__all__"
        widgets = {
            'newsletter_subject': TextInput(attrs={'size': 160}),
            'html_title': TextInput(attrs={'size': 128}),
            'meta_description': Textarea(),
        }


class CategoryAdmin(ModelAdmin):
    form = CategoryAdminForm
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
        ('Asunto de newsletter', {'fields': (('newsletter_automatic_subject', ), ('newsletter_subject', ))}),
        ('Metadatos', {'fields': (('html_title', ), ('meta_description', ))}),
    )
    raw_id_fields = ('full_width_cover_image', )


class ForeignKeyRawIdWidgetMoreWords(widgets.ForeignKeyRawIdWidget):
    """
    Overrided from django/contrib/admin/widgets.py
    To rise the quantity of words truncated in the last line of method.
    """
    def label_and_url_for_value(self, value):
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.model._default_manager.using(self.db).get(**{key: value})
        except (ValueError, self.rel.model.DoesNotExist, ValidationError):
            return '', ''

        try:
            url = reverse(
                '%s:%s_%s_change' % (
                    self.admin_site.name,
                    obj._meta.app_label,
                    obj._meta.object_name.lower(),
                ),
                args=(obj.pk,)
            )
        except NoReverseMatch:
            url = ''  # Admin not registered for target model.

        return Truncator(obj).words(30, truncate='...'), url


class CategoryHomeArticleForm(ModelForm):
    pos = IntegerField(label='orden', widget=TextInput(attrs={'size': 3, 'readonly': True}))

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
    verbose_name_plural = 'Artículos en portada'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Overrided from django/contrib/admin/options.py
        # Overrided with the only purpose to use the custom ForeignKeyRawIdWidgetMoreWords widget
        """
        Get a form Field for a ForeignKey.
        """
        db = kwargs.get('using')
        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = ForeignKeyRawIdWidgetMoreWords(db_field.remote_field, self.admin_site, using=db)
        elif db_field.name in self.radio_fields:
            kwargs['widget'] = widgets.AdminRadioSelect(attrs={
                'class': get_ul_class(self.radio_fields[db_field.name]),
            })
            kwargs['empty_label'] = _('None') if db_field.blank else None

        if 'queryset' not in kwargs:
            queryset = self.get_field_queryset(db, db_field, request)
            if queryset is not None:
                kwargs['queryset'] = queryset

        return db_field.formfield(**kwargs)

    class Media:
        css = {'all': ('css/category_home.css', )}


class CategoryHomeAdmin(admin.ModelAdmin):
    list_display = ('category', 'cover')
    exclude = ('articles', )
    inlines = [CategoryHomeArticleInline]

    def save_related(self, request, form, formsets, change):
        super(CategoryHomeAdmin, self).save_related(request, form, formsets, change)
        form.instance.dehole()

    def save_model(self, request, obj, form, change):
        super(CategoryHomeAdmin, self).save_model(request, obj, form, change)
        obj.dehole()


class CategoryNewsletterArticleForm(ModelForm):

    class Meta:
        fields = ['order', 'featured', 'article']
        model = CategoryNewsletterArticle
        widgets = {'order': TextInput(attrs={'size': 3})}


class CategoryNewsletterArticleInline(TabularInline):
    model = CategoryNewsletter.articles.through
    extra = 20
    max_num = 20
    form = CategoryNewsletterArticleForm
    fields = ('featured', 'article', 'order',)
    raw_id_fields = ('article', )
    verbose_name_plural = 'Artículos en newsletter'
    classes = ('dynamic-order',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Overrided from django/contrib/admin/options.py
        # Overrided with the only purpose to use the custom ForeignKeyRawIdWidgetMoreWords widget
        """
        Get a form Field for a ForeignKey.
        """
        db = kwargs.get('using')
        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = ForeignKeyRawIdWidgetMoreWords(db_field.remote_field, self.admin_site, using=db)
        elif db_field.name in self.radio_fields:
            kwargs['widget'] = widgets.AdminRadioSelect(attrs={
                'class': get_ul_class(self.radio_fields[db_field.name]),
            })
            kwargs['empty_label'] = _('None') if db_field.blank else None

        if 'queryset' not in kwargs:
            queryset = self.get_field_queryset(db, db_field, request)
            if queryset is not None:
                kwargs['queryset'] = queryset

        return db_field.formfield(**kwargs)

    class Media:
        js = (
            'admin/js/jquery%s.js' % ('' if settings.DEBUG else '.min'),
            'js/jquery-ui-1.12.1.custom.min.js',
            'js/homev2/dynamic_edition_admin.js',
            'js/RelatedObjectLookupsCustom.js',
        )
        css = {'all': ('css/category_newsletter.css', )}


class CategoryNewsletterAdmin(admin.ModelAdmin):
    list_display = ('category', 'valid_until', 'cover')
    exclude = ('articles', )
    inlines = [CategoryNewsletterArticleInline]
    fieldsets = (
        (None, {'fields': (('category', 'valid_until'), )}),
    )


class ArticleInline(TabularInline):
    model = BreakingNewsModule.articles.through
    extra = 3
    max_num = 3
    raw_id_fields = ('article', )
    verbose_name_plural = 'Artículos relacionados'


class BreakingNewsModuleAdmin(ModelAdmin):
    list_display = ('id', 'headline', 'deck', 'covers', 'is_published')
    list_editable = ('headline', 'is_published')
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
            kwargs["queryset"] = Article.published.all()
        return super(BreakingNewsModuleAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


class TagAdmin(admin.ModelAdmin):
    model = Tag
    search_fields = ('name',)


class TaggedItemAdmin(admin.ModelAdmin):
    model = TaggedItem
    search_fields = ('name',)


class DeviceSubscribedAdmin(admin.ModelAdmin):
    model = DeviceSubscribed
    list_display = ('user', 'time_created', 'browser')
    readonly_fields = ('user', 'time_created', 'subscription_info')
    search_fields = ['subscription_info', 'user__username', 'user__email', 'user__first_name', 'user__last_name']

    def browser(self, obj):
        endpoint = json.loads(obj.subscription_info)['endpoint']
        if 'updates.push.services.mozilla.com' in endpoint:
            return 'Mozilla Firefox'
        elif 'fcm.googleapis.com' in endpoint:
            return 'Google Chrome'
        else:
            return 'Navegador desconocido'


class PushNotificationAdmin(admin.ModelAdmin):
    model = PushNotification
    list_display = ('message', 'article', 'sent', 'tag')
    raw_id_fields = ('article',)
    actions = ['send_me_push_notification', 'send_push_notification_to_all']
    change_list_template = 'admin/overwrite_notification.html'
    readonly_fields = ('sent', 'tag')

    def send_notifications(self, request, queryset, all_users=True):
        def tag_as_id(notification, tag=None):
            notification.tag = notification.id if not tag else tag

        messages_sent = list(queryset.filter(sent__isnull=False).values_list('id', flat=True))
        if len(messages_sent) > 0:
            messages_sent = ','.join([str(item) for item in messages_sent])
            self.message_user(
                request,
                'Las notificaciones marcadas ya fueron enviadas, no se permite el re-envío',
                level=messages.ERROR,
                extra_tags='wn' + str(messages_sent),
            )
            return HttpResponseRedirect("./")
        for ms in queryset:
            with transaction.atomic():
                if ms.overwrite:
                    ar_id = ms.article.id
                    try:
                        tag = PushNotification.objects.filter(article__id=ar_id, sent__isnull=False).latest('sent').tag
                    except PushNotification.DoesNotExist:
                        tag = None
                    if tag:
                        tag_as_id(ms, tag)
                    else:
                        tag_as_id(ms)
                else:
                    tag_as_id(ms)
                send_push_notification(
                    ms.message,
                    ms.tag,
                    urljoin(settings.SITE_URL, ms.article.get_absolute_url()),
                    ms.article.photo.image.url if ms.article.photo else None,
                    None if all_users else request.user,
                )
                ms.sent = timezone.now()
                ms.save()
                self.message_user(
                    request,
                    'Las notificaciones selecciondas fueron correctamente agendadas para envío',
                    level=messages.SUCCESS,
                )

    def send_push_notification_to_all(self, request, queryset):
        # allow only to group members defined by setting
        restrict_group = getattr(settings, 'CORE_PUSH_NOTIFICATIONS_SENDALL_RESTRICT_GROUP', None)
        if (
            not request.user.is_superuser and restrict_group
            and Group.objects.get(name=restrict_group) not in request.user.groups.all()
        ):
            self.message_user(request, 'Permisos insuficientes para ejecutar esta acción', level=messages.ERROR)
        else:
            self.send_notifications(request, queryset)

    def send_me_push_notification(self, request, queryset):
        self.send_notifications(request, queryset, False)

    send_me_push_notification.short_description = \
        "Enviar las notificaciones seleccionadas solamente al usuario en la sesión actual (sólo a mi)."

    send_push_notification_to_all.short_description = "Enviar las notificaciones seleccionadas a todos los usuarios."


site.register(Article, ArticleAdmin)
site.register(Edition, EditionAdmin)
site.register(Journalist, JournalistAdmin)
site.register(Location, LocationAdmin)
site.register(PrintOnlyArticle, PrintOnlyArticleAdmin)
site.register(Section, SectionAdmin)
site.register(EditionHeader, EditionHeaderAdmin)
site.register(Supplement, SupplementAdmin)
site.register(Publication, PublicationAdmin)
site.register(Category, CategoryAdmin)
site.register(CategoryHome, CategoryHomeAdmin)
site.register(CategoryNewsletter, CategoryNewsletterAdmin)
site.register(BreakingNewsModule, BreakingNewsModuleAdmin)
site.unregister(Tag)
site.unregister(TaggedItem)
site.register(Tag, TagAdmin)
site.register(TaggedItem, TaggedItemAdmin)
site.register(DeviceSubscribed, DeviceSubscribedAdmin)
site.register(PushNotification, PushNotificationAdmin)
