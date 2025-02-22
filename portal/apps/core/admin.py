# -*- coding: utf-8 -*-
from requests.exceptions import ConnectionError
import json
from urllib.parse import urljoin
from pydoc import locate
from kombu.exceptions import OperationalError

from actstream.models import Action
from tagging.models import Tag, TaggedItem
from tagging.forms import TagField
from tagging_autocomplete_tagit.widgets import TagAutocompleteTagIt
from reversion.admin import VersionAdmin
from martor.models import MartorField
from martor.widgets import AdminMartorWidget

from django.conf import settings
from django.urls import path
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.messages import constants as messages
from django.contrib.admin import ModelAdmin, TabularInline, site, widgets
from django.forms import ModelForm, ValidationError, ChoiceField, RadioSelect, TypedChoiceField, Textarea, Widget
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.forms.fields import CharField, IntegerField
from django.forms.widgets import TextInput, HiddenInput
from django.shortcuts import get_object_or_404, render
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.text import Truncator
from django.utils.safestring import mark_safe

from .models import (
    Article,
    ArticleCollection,
    ArticleCollectionRelated,
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
from .choices import section_choices
from .templatetags.ldml import ldmarkup, cleanhtml
from .tasks import update_category_home, send_push_notification
from .utils import update_article_url_in_coral_talk, smart_quotes


class PrintOnlyArticleInline(TabularInline):
    model = PrintOnlyArticle
    extra = 10


"""
core.models.Edition model admin.
Articles related to editions are categorized into two distinct blocks in the admin add/change edition page:

- "Home Top": This block features articles prominently displayed on the home page. Although this scenario is less
  common, it is the most frequently used, as the database is expected to contain numerous editions, mirroring the
  periodic nature of news publications. In essence, this block represents the featured articles of an edition,
  regardless of whether it is currently displayed on the home page.

- "Non-Top Articles": This block comprises articles that are not featured in the edition.

- Implementation: The solution employs inline formsets to filter articles into one of these two blocks. The UI logic
  allows for the insertion of any article into either block, but not vice versa. To remove a featured article from an
  edition, it must first be removed from the "Home Top" block, after which it will appear in the "Non-Top Articles"
  block, enabling its removal from the edition. Note that dragging articles across blocks is not currently supported,
  but may be implemented in the future.

Happy publishing!
"""


class TopArticleRelBaseInlineFormSet(BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.filter(home_top=True)

    def clean(self):
        # this also can be done using javascript after add a new row or drag the row to a new position
        # but allways is a good practice to make server side validation
        # TODO: 1. DRY: this can be encapsulated in a new base class method receiving the order field name
        #               (be caution with the last condition, the one after "DELETE")
        #       2. Test cases, as many combinations as possible of this actions:
        #          1 - Untouched form
        #          2 - Empty form, add rows
        #          3 - drag
        #          4 - unmark featured
        #          5 - mark featured
        #          6 - delete
        super().clean()
        last_idx = 0
        for form in self.forms:
            f_cleaned_data = form.cleaned_data
            if f_cleaned_data and not f_cleaned_data.get('DELETE') and f_cleaned_data.get('home_top'):
                position = f_cleaned_data.get('top_position')
                if position:
                    if position > last_idx:
                        last_idx = position
                else:
                    last_idx += 1
                    form.cleaned_data['top_position'] = form.instance.top_position = last_idx
            # if for any reason the article has not position, set it = 1
            if not form.cleaned_data.get('position'):
                form.cleaned_data['position'] = form.instance.position = 1


class NoTopArticleRelBaseInlineFormSet(BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.filter(home_top=False)

    def clean(self):
        # this also can be done using javascript after add a new row or drag the row to a new position
        # but allways is a good practice to make server side validation
        super().clean()
        last_idx = 0
        for form in self.forms:
            f_cleaned_data = form.cleaned_data
            if f_cleaned_data and not f_cleaned_data.get('DELETE') and not f_cleaned_data.get('home_top'):
                position = f_cleaned_data.get('position')
                if position:
                    if position > last_idx:
                        last_idx = position
                else:
                    last_idx += 1
                    form.cleaned_data['position'] = form.instance.position = last_idx


class ArticleRelAdminBaseModelForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['article'].label = 'artículo'
        self.fields['section'].label = 'sección'
        self.fields['section'].choices = section_choices()
        self.fields['home_top'].label = 'en portada'

    class Meta:
        model = ArticleRel
        fields = "__all__"


class ReadOnlyDisplayWidget(Widget):
    # TODO: a better base class to inherit from would be HiddenInput using readonly=True by default, try to do it.

    def render(self, name, value, attrs=None, renderer=None):
        text_display = f'<span>{value if value is not None else ""}</span>'
        hidden_input = f'<input type="hidden" id="{name}" name="{name}" value="{value}"/>'
        return mark_safe(text_display + hidden_input)


class ArticleRelHomeTopForm(ArticleRelAdminBaseModelForm):
    top_position = IntegerField(
        label='posición',
        widget=ReadOnlyDisplayWidget(attrs={'size': 3, 'readonly': True}),
        help_text=(
            'Arrastre la fila del artículo deseado hacia abajo o arriba para cambiar su posición en '
            'portada; las posiciones serán recalculadas al guardar la edición con esta página.'
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['home_top'].help_text = \
            'Utilice esta opción para desmarcar y poder quitar el artículo de los artículos en portada.'
        self.initial['home_top'] = True

    class Meta:
        model = ArticleRel
        fields = "__all__"


class ArticleRelHomeNoTopForm(ArticleRelAdminBaseModelForm):
    # TODO: draggable ordering is not working, FIX asap

    position = IntegerField(
        label='orden',
        widget=ReadOnlyDisplayWidget(attrs={'size': 3, 'readonly': True}),
        help_text=(
            'Arrastre la fila del artículo deseado hacia abajo o arriba para cambiar su orden en '
            'la edición; los valores serán recalculados al guardar la edición con esta página.'
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['home_top'].help_text = 'Marque esta opción para agregar el artículo en portada.'

    class Meta:
        model = ArticleRel
        fields = "__all__"


class EditionBaseArticleInline(TabularInline):
    model = ArticleRel
    extra = 0
    raw_id_fields = ('article',)
    classes = ('dynamic-order',)

    class Media:
        # jquery loaded again (admin uses custom js namespaces and we use jquery-ui)
        js = (
            'admin/js/jquery.js',
            'js/jquery-ui-1.13.2.custom.min.js',
            'js/homev2/dynamic_edition_admin.js',
            'js/RelatedObjectLookupsCustom.js',
        )
        css = {'all': ('css/home_admin.css',)}


TopArticleRelInlineFormSet = inlineformset_factory(
    Edition,
    ArticleRel,
    form=ArticleRelHomeTopForm,
    formset=TopArticleRelBaseInlineFormSet,
)
NoTopArticleRelInlineFormSet = inlineformset_factory(
    Edition,
    ArticleRel,
    form=ArticleRelHomeNoTopForm,
    formset=NoTopArticleRelBaseInlineFormSet,
)


class HomeTopArticleInline(EditionBaseArticleInline):
    ordering = ('top_position',)
    fields = ('top_position', 'article', 'section', "home_top")
    verbose_name = 'artículo destacado'
    verbose_name_plural_default = 'artículos destacados en portada'
    verbose_name_plural = verbose_name_plural_default
    form = ArticleRelHomeTopForm
    formset = TopArticleRelInlineFormSet
    can_delete = False

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if (
            obj
            and obj.publication.slug == settings.DEFAULT_PUB
            and self.verbose_name_plural == self.verbose_name_plural_default
        ):
            self.verbose_name_plural += " principal"
        return fieldsets


class NoHomeTopArticleInline(EditionBaseArticleInline):
    ordering = ('position',)
    fields = ('position', 'article', 'section', "home_top")
    verbose_name = 'artículo'
    verbose_name_plural = 'artículos'
    form = ArticleRelHomeNoTopForm
    formset = NoTopArticleRelInlineFormSet


@admin.register(Edition, site=site)
class EditionAdmin(ModelAdmin):
    fields = ('date_published', 'pdf', 'cover', 'publication')
    list_display = ('edition_pub', 'title', 'pdf', 'cover', 'get_supplements')
    list_filter = ('date_published', 'publication')
    search_fields = ('title',)
    date_hierarchy = 'date_published'
    publication = None
    inlines = [HomeTopArticleInline, NoHomeTopArticleInline]

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            self.publication = obj.publication
        return super().get_form(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'cover':
            kwargs['queryset'] = self.articles_qs
            return db_field.formfield(**kwargs)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                'add_article/<int:ed_id>/<int:sec_id>/<int:art_id>/',
                self.admin_site.admin_view(self.add_article),
            ),
        ]
        return my_urls + urls

    def add_article(self, request, ed_id, sec_id, art_id):
        edition = get_object_or_404(Edition, pk=ed_id)
        section = get_object_or_404(Section, pk=sec_id)
        article = get_object_or_404(Article, pk=art_id)
        ArticleRel.objects.create(edition=edition, section=section, article=article)
        return HttpResponseRedirect("/admin/core/edition/" + ed_id)  # TODO: use "reverse" to build the target url

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        update_category_home()


class PortableDocumentFormatPageAdmin(ModelAdmin):
    pass


class SectionAdminModelForm(ModelForm):
    # TODO: use this form to validate for ex. when a Section cannot be saved (dupe slug or anything)

    class Meta:
        fields = "__all__"
        widgets = {'html_title': TextInput(attrs={'size': 128}), 'meta_description': Textarea()}


@admin.register(Section, site=site)
class SectionAdmin(ModelAdmin):
    form = SectionAdminModelForm
    list_editable = ('name', 'home_order', 'in_home')
    list_filter = ('category', 'in_home', 'home_block_all_pubs', 'home_block_show_featured', "publications")
    list_display = (
        'id',
        'home_order',
        'name',
        'category',
        "included_in_category_menu_short",
        'in_home',
        'get_publications',
        'articles_count',
    )
    search_fields = ('name', 'name_in_category_menu', 'contact')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('name', 'category'),
                    ('name_in_category_menu', "included_in_category_menu"),
                    ('description', 'show_description'),
                    ('home_order', 'white_text', 'background_color'),
                    ('publications',),
                    ('in_home', 'home_block_all_pubs'),
                    ('home_block_show_featured',),
                    ('imagen', 'show_image'),
                    ('contact',),
                ),
            },
        ),
        ('Metadatos', {'fields': (('html_title',), ('meta_description',))}),
    )

    def included_in_category_menu_short(self, instance):
        return instance.included_in_category_menu
    included_in_category_menu_short.short_description = "en menú de área"
    included_in_category_menu_short.boolean = True

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        update_category_home()


class ArticleExtensionInline(TabularInline):
    model = ArticleExtension
    extra = 1
    classes = ["collapse"]


class ArticleBodyImageInline(TabularInline):
    model = ArticleBodyImage
    extra = 0
    raw_id_fields = ('image', )
    readonly_fields = ['photo_admin_thumbnail', 'photo_date_taken', 'photo_date_added']
    classes = ["collapse"]

    @admin.display(
        description='thumbnail'
    )
    def photo_admin_thumbnail(self, instance):
        return instance.image.admin_thumbnail()

    @admin.display(
        description='tomada el'
    )
    def photo_date_taken(self, instance):
        return instance.image.date_taken

    @admin.display(
        description='fecha de creación'
    )
    def photo_date_added(self, instance):
        return instance.image.date_added


class ArticleRelAdminModelForm(ArticleRelAdminBaseModelForm):
    main = ChoiceField(label='principal', widget=RadioSelect, choices=((1, ''), ), required=False)


class ArticleEditionInline(TabularInline):
    verbose_name = verbose_name_plural = 'publicado en'
    model = ArticleRel
    raw_id_fields = ('edition',)
    form = ArticleRelAdminModelForm
    extra = 1
    classes = ["collapse"]


class UtopiaCmsAdminMartorWidget(AdminMartorWidget):
    """
    Overrided to use a custom js, because we found this error in the upstream project:
    https://github.com/agusmakmun/django-markdown-editor/pull/217
    """

    @property
    def media(self):
        result = super().media
        js_files = list(result._js_lists[1])
        js_files[js_files.index('martor/js/martor.bootstrap.min.js')] = "js/martor/utopiacms.martor.bootstrap.js"
        result._js_lists[1] = js_files
        return result


class ArticleAdminModelForm(ModelForm):
    PW_OPTIONS = (
        ('none', 'Metered (por defecto)'),
        ('full_restricted_true', 'Hard (solamente para suscriptores)'),
        ('public_true', 'Sin paywall (libre acceso)'),
    )
    slug = CharField(
        label='Slug',
        widget=TextInput(attrs={'readonly': 'readonly'}),
        help_text='Se genera automáticamente en base al título.',
    )
    tags = TagField(widget=TagAutocompleteTagIt(max_tags=False), required=False)
    pw_radio_choice = ChoiceField(
        label="Paywall", choices=PW_OPTIONS, widget=RadioSelect(attrs={'style': 'display: block;'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.full_restricted and not self.instance.public:
            self.initial['pw_radio_choice'] = 'full_restricted_true'
        elif not self.instance.full_restricted and self.instance.public:
            self.initial['pw_radio_choice'] = 'public_true'
        else:
            self.initial['pw_radio_choice'] = 'none'
        nowval = timezone.now()
        if not self.instance.pk:
            self.initial['date_published'] = nowval
        self.fields['date_published'].widget.attrs['min'] = nowval.isoformat()
        self.fields['date_published'].required = False
        self.fields['date_published'].label = ""

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
        # TODO: "add" errors right way (as django doc says) instead of raising them
        if self.errors:
            raise ValidationError("")

        cleaned_data = super().clean()
        if cleaned_data.get("ipfs_upload") and not getattr(settings, "IPFS_TOKEN", None):
            raise ValidationError("La configuración necesaria para publicar en IPFS no está definida.")

        # TODO: DRY (Article.save does the same logic)
        nowval = timezone.now()
        date_published = cleaned_data.get('date_published')
        is_published, to_be_published = cleaned_data.get('is_published'), cleaned_data.get('to_be_published')

        if is_published:
            if to_be_published:
                self.add_error(None, 'No se permite programar publicación de un artículo ya publicado')
        elif to_be_published:
            if not date_published:
                self.add_error(None, 'Para programar la publicación de un artículo se debe especificar la fecha')
            elif date_published <= nowval:
                self.add_error(None, 'La fecha de publicación programada no puede estar en el pasado')

        if self.errors:
            raise ValidationError("")

        date_value = (date_published if is_published else cleaned_data.get('date_created')) or nowval
        # conversion to UTC is needed, it's not done automatically like Article.save does.
        # (save gets values from obj and not from the form), TODO: improve or investigate to explain better the cause.
        date_value = timezone.localtime(
            timezone.datetime(
                date_value.year,
                date_value.month,
                date_value.day,
                date_value.hour,
                date_value.minute,
                date_value.second,
                date_value.microsecond,
                tzinfo=timezone.get_default_timezone(),
            ),
            timezone.utc,
        )
        targets = Article.objects.filter(
            Q(is_published=True) & Q(date_published__year=date_value.year) & Q(date_published__month=date_value.month)
            | Q(is_published=False) & Q(date_created__year=date_value.year) & Q(date_created__month=date_value.month),
            slug=slugify(cleanhtml(ldmarkup(smart_quotes(cleaned_data.get('headline'))))),
        )
        if self.instance.id:
            targets = targets.exclude(id=self.instance.id)
        if targets:
            raise ValidationError('Ya existe un artículo en ese mes con el mismo título.')

        # pw options:
        pw_choice = cleaned_data.get('pw_radio_choice')
        if pw_choice == 'none':
            cleaned_data['full_restricted'] = False
            cleaned_data['public'] = False
        elif pw_choice == 'full_restricted_true':
            cleaned_data['full_restricted'] = True
            cleaned_data['public'] = False
        elif pw_choice == 'public_true':
            cleaned_data['full_restricted'] = False
            cleaned_data['public'] = True

        return cleaned_data

    class Meta:
        model = Article
        fields = "__all__"
        widgets = {"full_restricted": HiddenInput(), "public": HiddenInput()}


@admin.display(description='Foto', boolean=True)
def has_photo(obj):
    return bool(obj.photo is not None)


@admin.display(description='Galería', boolean=True)
def has_gallery(obj):
    return bool(obj.gallery is not None)


article_optional_inlines = []
if 'core.attachments' in settings.INSTALLED_APPS:
    from core.attachments.models import Attachment

    class AttachmentInline(TabularInline):
        model = Attachment
        extra = 1
        classes = ["collapse"]

    article_optional_inlines.append(AttachmentInline)


def get_editions():
    since = timezone.now().date() - timezone.timedelta(days=5)
    return Edition.objects.filter(date_published__gte=since)


@admin.register(Article, site=site)
class ArticleAdmin(VersionAdmin):
    # TODO: Do not allow delete if the article is the main article in a category home (home.models.Home)
    actions = ["toggle_published"]
    form = ArticleAdminModelForm
    formfield_overrides = {MartorField: {"widget": UtopiaCmsAdminMartorWidget}}
    prepopulated_fields = {'slug': ('headline',)}
    filter_horizontal = ('byline',)
    list_display = (
        'id',
        'headline',
        'type',
        'get_publications',
        'get_sections',
        'creation_date',
        'publication_date',
        "published_status",
        has_photo,
        'surl',
    )
    list_select_related = True
    list_filter = (
        'type', 'date_created', 'is_published',
        # 'to_be_published',  # TODO: add this filter when the field gets fully implemented
        'date_published', 'newsletter_featured', 'byline'
    )
    search_fields = ['headline', 'slug', 'deck', 'lead', 'body']
    date_hierarchy = 'date_published'
    ordering = ('-date_created',)
    raw_id_fields = ('photo', 'gallery', "audio", 'main_section')
    inlines = article_optional_inlines + [ArticleExtensionInline, ArticleBodyImageInline, ArticleEditionInline]
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'type',
                    'headline',
                    'alt_title_metadata',
                    'alt_title_newsletters',
                    'slug',
                    'keywords',
                    'deck',
                    'alt_desc_metadata',
                    'alt_desc_newsletters',
                    'lead',
                    'body',
                ),
                'classes': ('wide',)
            },
        ),
        (
            'Portada',
            {
                'fields': ('home_lead', 'home_top_deck', 'home_display', 'home_header_display', 'header_display'),
                'classes': ('wide',),
            },
        ),
        (
            'Metadatos',
            {
                'fields': (
                    (
                        'is_published',
                        # 'to_be_published',  # TODO: add this field when it gets fully implemented
                        'date_published'
                    ),
                    'tags',
                    'main_section'
                )
            }
        ),
        ('Autor', {'fields': ('byline', 'only_initials', 'location'), 'classes': ('collapse',)}),
        ('Multimedia', {'fields': ('photo', 'gallery', 'video', 'youtube_video', 'audio'), 'classes': ('collapse',)}),
        (
            'Avanzado',
            {
                'fields': (
                    'allow_comments',
                    'allow_related',
                    'show_related_articles',
                    'newsletter_featured',
                    "pw_radio_choice",
                    "full_restricted",
                    "public",
                )
                + (('additional_access',) if Publication.multi() else ())
                + ('latitude', 'longitude', 'ipfs_upload'),
                'classes': ('collapse',),
            },
        ),
    )

    @admin.action(description="Intercambiar estado de publicación: publicado <-> borrador")
    def toggle_published(self, request, queryset):
        if 'apply' in request.POST:
            success_counter, error_counter = 0, 0
            if queryset.filter(to_be_published=True).exists():
                self.message_user(request, "No se pueden seleccionar artículos programados para ejecutar esta acción")
            else:
                for article in queryset:
                    article.is_published = not article.is_published
                    try:
                        article.save()
                    except Exception:
                        error_counter += 1
                    else:
                        success_counter += 1
            if success_counter:
                self.message_user(request, "Fueron modificados {} artículo(s)".format(success_counter))
            if error_counter:
                self.message_user(
                    request,
                    "Hubo error al intentar modificar{} artículo(s)".format(error_counter),
                    level=messages.ERROR,
                )
            return HttpResponseRedirect(request.get_full_path())
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(request.get_full_path())
        return render(request, "admin/toggle_published_intermediate.html", {"articles": queryset})

    def get_urls(self):
        return [
            path(
                "<path:object_id>/history_adminlog/",
                self.admin_site.admin_view(self.adminlog_history_view),
                name="%s_%s_history_adminlog" % (self.model._meta.app_label, self.model._meta.model_name),
            ),
        ] + super().get_urls()

    @admin.display(description='Creado', ordering='date_created')
    def creation_date(self, obj):
        return timezone.template_localtime(obj.date_created).strftime("%d %b %Y %H:%M")

    @admin.display(description='Estado')
    def published_status(self, obj):
        result = "Borrador"
        if obj.is_published:
            result = "" if obj.to_be_published else "Publicado"
        elif obj.to_be_published:
            result = "Programado"
        return result

    @admin.display(description='Publicado', ordering='date_published')
    def publication_date(self, obj):
        if obj.is_published and obj.date_published:
            return timezone.template_localtime(obj.date_published).strftime("%d %b %Y %H:%M")
        else:
            return ''

    def get_object(self, request, object_id, from_field=None):
        # Hook obj for use in formfield_for_manytomany
        self.obj = super().get_object(request, object_id)
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
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'publication':
            return db_field.formfield(**kwargs)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if form.is_valid():
            try:
                obj.admin = True  # tell model's save method that we are calling it from the admin
                super().save_model(request, obj, form, change)
                self.obj = obj
            except Exception as e:
                if settings.DEBUG:
                    print("DEBUG: error in core.admin.ArticleAdmin.save_model: %s" % e)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

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

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Conditions to redirect to the collection change view:
        - This is not already the change view of a collection
        - The object to change is a colection
        - The user has permissions to change a collection
        """
        try:
            article = Article.objects.get(id=object_id)
        except Article.DoesNotExist:
            pass
        else:
            if (
                type(site._registry[ArticleCollection]) is not type(self)
                and hasattr(article, "articlecollection")
                and request.user.has_perm('core.change_articlecollection')
            ):
                return HttpResponseRedirect(
                    reverse(
                        '%s:%s_articlecollection_change' % (self.admin_site.name, article._meta.app_label),
                        args=(object_id, ),
                    )
                )
        return super().change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        if 'type__exact' not in request.GET:
            q = request.GET.copy()
            q['type__exact'] = 'NE'  # Setea el filtro por defecto a noticias
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super().changelist_view(request, extra_context=extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        # actstream does not return unicode when rendering an Action if the target object has non-ascii chars,
        # this breaks the django six names collector, and this temporal change can hack this when deleting an article.
        # TODO: check if this issue is still present in py3
        Action.__str__ = lambda x: 'Article followed by user'
        response = super().delete_view(request, object_id, extra_context)
        del Action.__str__
        return response

    def adminlog_history_view(self, request, object_id, extra_context=None):
        object_history_template_bak = self.object_history_template
        self.object_history_template = None
        response = super(VersionAdmin, self).history_view(request, object_id)
        self.object_history_template = object_history_template_bak
        return response

    class Media:
        css = {'all': ('css/charcounter.css', 'css/admin_article.css')}
        js = (
            'js/jquery.charcounter-orig.js',
            'js/utopiacms_martor_semantic.js',
            'js/utopiacms_martor_fullheight.js',
            'js/homev2/article_admin.js',
        )


class ForeignKeyRawIdWidgetMoreWords(widgets.ForeignKeyRawIdWidget):
    """
    Overrided from django/contrib/admin/widgets.py
    To rise the quantity of words truncated in the last line of method.
    """
    utopia_words = 30

    def label_and_url_for_value(self, value):
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.model._default_manager.using(self.db).get(**{key: value})
        except (ValueError, self.rel.model.DoesNotExist, ValidationError):
            return '', ''

        try:
            url = reverse(
                '%s:%s_%s_change' % (self.admin_site.name, obj._meta.app_label, obj._meta.object_name.lower()),
                args=(obj.pk, ),
            )
        except NoReverseMatch:
            url = ''  # Admin not registered for target model.

        return Truncator(obj).words(self.utopia_words, truncate='...'), url


class ForeignKeyRawIdWidgetMoreWords20(ForeignKeyRawIdWidgetMoreWords):
    utopia_words = 20


class ArticleCollectionRelatedForm(ModelForm):

    class Meta:
        fields = ['position', 'article']
        model = ArticleCollectionRelated
        widgets = {
            'position': TextInput(attrs={'size': 3}),
            "article": ForeignKeyRawIdWidgetMoreWords20(
                CategoryHomeArticle._meta.get_field("article").remote_field, site
            )
        }


class ArticleCollectionRelatedFormSet(BaseInlineFormSet):
    """
    For validation purposes, taken from: https://stackoverflow.com/a/1884760
    min_num and validate_min better options cannot be used because the validation we want also depends on other fields.
    """
    def is_valid(self):
        return super().is_valid() and not any([bool(e) for e in self.errors])

    def clean(self):
        if self.data.get('is_published') and not getattr(settings, "CORE_ALLOW_EMPTY_COLLECTIONS", True):
            # get forms that actually have valid data
            count = 0
            for form in self.forms:
                try:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        count += 1
                except AttributeError:
                    # annoyingly, if a subform is invalid Django explicity raises
                    # an AttributeError for cleaned_data
                    pass
            if count < 1:
                raise ValidationError("No se permite publicar una colección sin artículos relacionados.")


class ArticleCollectionRelatedInline(TabularInline):
    model = ArticleCollection.related_articles.through
    fk_name = "collection"
    form = ArticleCollectionRelatedForm
    formset = ArticleCollectionRelatedFormSet
    raw_id_fields = ('article', )
    verbose_name_plural = 'Artículos vinculados'
    classes = ["collapse"]

    class Media:
        css = {'all': ('css/article_collection_related.css', )}


@admin.register(ArticleCollection, site=site)
class ArticleCollectionAdmin(ArticleAdmin):
    fieldsets = ArticleAdmin.fieldsets + (("Colección", {"fields": ("traversal_categorization", )}), )
    inlines = ArticleAdmin.inlines + [ArticleCollectionRelatedInline]


@admin.register(EditionHeader, site=site)
class EditionHeaderAdmin(ModelAdmin):
    list_display = ('edition', 'title', 'subtitle')
    fieldsets = ((None, {'fields': list_display}), )
    search_fields = list_editable = ['title', 'subtitle']
    raw_id_fields = ['edition']


@admin.register(Supplement, site=site)
class SupplementAdmin(ModelAdmin):
    fieldsets = ((None, {'fields': ('edition', 'name', 'headline', 'pdf', 'public')}), )
    date_hierarchy = 'date_published'
    list_display = ('name', 'edition', 'date_published', 'pdf', 'cover', 'public')
    list_filter = ('name', 'date_created', 'public')
    search_fields = ['name', 'date_published']
    raw_id_fields = ['edition']


@admin.register(PrintOnlyArticle, site=site)
class PrintOnlyArticleAdmin(ModelAdmin):
    list_display = ('headline', 'deck', 'edition')
    list_filter = ('date_created', )
    search_fields = ['headline', 'deck']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'edition':
            kwargs['queryset'] = get_editions()
            return db_field.formfield(**kwargs)
        return super(ArticleAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


@admin.display(
    description='Artículos publicados'
)
def published_articles(obj):
    return obj.articles_core.filter(is_published=True).count()


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


@admin.register(Journalist, site=site)
class JournalistAdmin(ModelAdmin):
    form = JournalistForm
    list_display = ('name', 'job', published_articles)
    list_filter = ('job',)
    search_fields = ['name']
    fieldsets = (
        (None, {'fields': ('name', 'email', 'image', 'bio', 'job', 'sections')}),
        (
            'Redes sociales',
            {
                'description': 'Ingrese enlace completo al respectivo perfil.(ej: https://example.com/perfil)',
                'fields': (
                    'bs',
                    'fb',
                    'tt',
                    'ig',
                    'mtdn',
                    'thds',
                    'ytb',
                    'lnkin',
                    'tktk',
                    'tr',
                    'tw',
                    'other_one',
                    'other_two',
                    'other_three',
                ),
            },
        ),
    )


@admin.register(Location, site=site)
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
        cleaned_data = super().clean()
        if cleaned_data.get('newsletter_automatic_subject') is False and not cleaned_data.get('newsletter_subject'):
            raise ValidationError('Se debe incluir un asunto de newsletter al configurarlo como "manual".')


class PublicationAdminForm(CustomSubjectAdminForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['extra_context'].required = False  # this was needed to avoid "field required" error

    class Meta:
        model = Publication
        fields = "__all__"
        widgets = {
            'newsletter_tagline': TextInput(attrs={'size': 160}),
            'newsletter_subject': TextInput(attrs={'size': 160}),
            'html_title': TextInput(attrs={'size': 128}),
            'meta_description': Textarea(),
            "extra_context": Textarea(attrs={"spellcheck": "false", "style": "width:80%"}),
        }


@admin.register(Publication, site=site)
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
    raw_id_fields = ('full_width_cover_image',)
    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('name', 'image'),
                    ('twitter_username',),
                    ('description',),
                    ('slug', 'headline', 'weight'),
                    ('public', 'has_newsletter', "newsletter_new_pill"),
                    ('newsletter_name', 'newsletter_logo'),
                    ('newsletter_tagline',),
                    ('newsletter_periodicity', 'newsletter_header_color'),
                    ('newsletter_campaign', 'subscribe_box_question'),
                    ('subscribe_box_nl_subscribe_auth', 'subscribe_box_nl_subscribe_anon'),
                    ('full_width_cover_image',),
                    ('is_emergente', 'new_pill'),
                ),
            },
        ),
        ('Custom template data', {'fields': ('extra_context',), "classes": ("monospace",)}),
        ('Asunto de newsletter', {'fields': (('newsletter_automatic_subject', ), ('newsletter_subject',))}),
        (
            'Metadatos',
            {
                'fields': (
                    ('html_title',),
                    ('meta_description',),
                    ('icon', 'icon_png'),
                    ('icon_png_16', 'icon_png_32'),
                    ('apple_touch_icon_180',),
                    ('apple_touch_icon_192',),
                    ('apple_touch_icon_512',),
                    ('open_graph_image',),
                    ('open_graph_image_width', 'open_graph_image_height'),
                    ('publisher_logo',),
                    ('publisher_logo_width', 'publisher_logo_height'),
                ),
            },
        ),
    )
    actions = ['send_newsletter']

    def get_changelist_form(self, request, **kwargs):
        kwargs.setdefault('form', PublicationAdminChangelistForm)
        return super().get_changelist_form(request, **kwargs)

    @admin.action(description="Enviar la newsletter de la publicación seleccionada")
    def send_newsletter(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(
                request,
                "No se permite enviar más de una newsletter a la vez, seleccione solamente una publicación",
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


class CategoryAdminForm(CustomSubjectAdminForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['newsletter_extra_context'].required = False  # this was needed to avoid "field required" error

    class Meta:
        model = Category
        fields = "__all__"
        widgets = {
            'newsletter_subject': TextInput(attrs={'size': 160}),
            'html_title': TextInput(attrs={'size': 128}),
            'meta_description': Textarea(),
            "newsletter_extra_context": Textarea(attrs={"spellcheck": "false", "style": "width:80%"}),
        }


@admin.register(Category, site=site)
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
                    ('exclude_from_top_menu', 'dropdown_menu'),
                    ('title', 'more_link_title', 'new_pill'),
                    ('description',),
                    ('full_width_cover_image', 'full_width_cover_image_title'),
                    ('full_width_cover_image_lead',),
                    ('has_newsletter', "newsletter_new_pill"),
                    ("newsletter_from_name", "newsletter_from_email"),
                    ('newsletter_tagline', 'newsletter_periodicity'),
                    ('subscribe_box_question',),
                    ('subscribe_box_nl_subscribe_auth',),
                    ('subscribe_box_nl_subscribe_anon',),
                ),
            },
        ),
        ('Asunto de newsletter', {'fields': (('newsletter_automatic_subject',), ('newsletter_subject',))}),
        ('Newsletter custom template data', {'fields': ('newsletter_extra_context',), "classes": ("monospace",)}),
        ('Metadatos', {'fields': (('html_title',), ('meta_description',))}),
    )
    raw_id_fields = ('full_width_cover_image',)


class CategoryHomeArticleForm(ModelForm):
    position = IntegerField(label='orden', widget=ReadOnlyDisplayWidget(attrs={'size': 3, 'readonly': True}))

    class Meta:
        fields = ['position', 'home', 'article', 'fixed']
        model = CategoryHomeArticle
        widgets = {
            "article": ForeignKeyRawIdWidgetMoreWords(
                CategoryHomeArticle._meta.get_field("article").remote_field, site
            )
        }


CategoryHomeArticleFormSetBase = inlineformset_factory(CategoryHome, CategoryHomeArticle, form=CategoryHomeArticleForm)


class CategoryHomeArticleFormSet(CategoryHomeArticleFormSetBase):

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if index is not None:
            form.fields["position"].initial = index + 1


class CategoryHomeArticleInline(TabularInline):
    model = CategoryHome.articles.through
    max_num = getattr(settings, "CORE_UPDATE_CATEGORY_HOMES_ARTICLES_INLINE_MAX_NUM", 20)
    extra = max_num
    form = CategoryHomeArticleForm
    formset = CategoryHomeArticleFormSet
    raw_id_fields = ('article',)
    verbose_name_plural = 'Artículos en portada'
    classes = ('dynamic-order',)

    class Media:
        js = ('admin/js/jquery.js', 'js/jquery-ui-1.13.2.custom.min.js', 'js/homev2/dynamic_edition_admin.js')
        css = {'all': ('css/category_home.css',)}


@admin.register(CategoryHome, site=site)
class CategoryHomeAdmin(admin.ModelAdmin):
    list_display = ('category', 'cover')
    exclude = ('articles',)
    inlines = [CategoryHomeArticleInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.dehole()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.dehole()


class CategoryNewsletterArticleForm(ModelForm):

    class Meta:
        fields = ['order', 'featured', 'article']
        model = CategoryNewsletterArticle
        widgets = {
            'order': TextInput(attrs={'size': 3}),
            "article": ForeignKeyRawIdWidgetMoreWords(
                CategoryNewsletterArticle._meta.get_field("article").remote_field, site
            ),
        }


class CategoryNewsletterArticleInline(TabularInline):
    model = CategoryNewsletter.articles.through
    extra = 20
    max_num = 20
    form = CategoryNewsletterArticleForm
    fields = ('featured', 'article', 'order')
    raw_id_fields = ('article', )
    verbose_name_plural = 'Artículos en newsletter'
    classes = ('dynamic-order', )

    class Media:
        # jquery loaded again (admin uses custom js namespaces and we use jquery-ui)
        js = (
            'admin/js/jquery.js',
            'js/jquery-ui-1.13.2.custom.min.js',
            'js/homev2/dynamic_edition_admin.js',
            'js/RelatedObjectLookupsCustom.js',
        )
        css = {'all': ('css/category_newsletter.css', )}


@admin.register(CategoryNewsletter, site=site)
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


@admin.register(BreakingNewsModule, site=site)
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
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name in ('deck', 'embeds_description', 'notification_text'):
            field.widget.attrs['style'] = 'width:50em;'
        elif db_field.name in ('publications', 'categories'):
            field.widget.attrs['size'] = max((Publication.objects.count(), Category.objects.count()))
        return field

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "articles":
            kwargs["queryset"] = Article.published.all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class TagAdmin(admin.ModelAdmin):
    model = Tag
    search_fields = ('name',)


class TaggedItemAdmin(admin.ModelAdmin):
    model = TaggedItem
    search_fields = ('name',)


@admin.register(DeviceSubscribed, site=site)
class DeviceSubscribedAdmin(admin.ModelAdmin):
    # TODO: derive from a new baseclass who handles an action post with more fields than DATA_MAX... (show a message
    #       error instead of error 500)
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


@admin.register(PushNotification, site=site)
class PushNotificationAdmin(admin.ModelAdmin):
    # TODO: adjust change_list columns width
    model = PushNotification
    list_display = ('message', 'article', 'sent', 'tag')
    raw_id_fields = ('article',)
    actions = ['send_me_push_notification', 'send_push_notification_to_all']
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
            return HttpResponseRedirect("./")  # TODO: use "reverse" to build the target url
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
                try:
                    send_push_notification(
                        ms.message,
                        ms.tag,
                        urljoin(settings.SITE_URL, ms.article.get_absolute_url()),
                        ms.article.photo.image.url if ms.article.photo else None,
                        None if all_users else request.user,
                    )
                except OperationalError as oe_exc:
                    msg = "ERROR: send_push_notification_task could not be started (%s)" % oe_exc
                    msg_level = messages.ERROR
                else:
                    ms.sent = timezone.now()
                    ms.save()
                    msg = 'Las notificaciones selecciondas fueron correctamente agendadas para envío'
                    msg_level = messages.SUCCESS
                self.message_user(request, msg, level=msg_level)

    @admin.action(description="Enviar las notificaciones seleccionadas a todos los usuarios.")
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

    @admin.action(
        description="Enviar las notificaciones seleccionadas solamente al usuario en la sesión actual (sólo a mi)."
    )
    def send_me_push_notification(self, request, queryset):
        self.send_notifications(request, queryset, False)


site.unregister(Tag)
site.unregister(TaggedItem)
site.register(Tag, TagAdmin)
site.register(TaggedItem, TaggedItemAdmin)
