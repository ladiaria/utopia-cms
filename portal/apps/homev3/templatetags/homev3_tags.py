# -*- coding: utf-8 -*-

from django.conf import settings
from django.template import Library, Engine, TemplateDoesNotExist, loader
from django.template.base import Node

from core.models import Section, Publication, Category, get_current_edition
from core.utils import get_category_template, get_articles_slider_template


register = Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


class RenderSectionNode(Node):
    def __init__(self, context, section_slug, article_type, top_index):
        self.section_slug = section_slug
        self.article_type = article_type
        self.top_index = top_index

    def render(self, context):
        result, edition = '', context.get('edition')

        if edition:
            try:
                section = Section.objects.get(slug=self.section_slug)
            except Exception:
                section = None

            articles, top_articles = [], context.get('destacados')
            template = 'section_custom/common.html'

            if self.top_index:

                articles = top_articles[self.top_index:self.top_index + 4]
                template = 'section_row.html'

            elif section and section.in_home:

                template_dir = getattr(settings, "CORE_RENDER_SECTION_TEMPLATE_DIR", None)
                if template_dir:
                    template_try = '%s/%s.html' % (template_dir, section.slug)
                    template_engine = Engine.get_default()
                    try:
                        template_engine.get_template(template_try)
                    except TemplateDoesNotExist:
                        pass
                    else:
                        template = template_try

                if section.slug not in getattr(settings, 'CORE_RENDER_SECTION_ARTICLES_TEMPLATE_OVERRIDES', ()):

                    latest_kwargs = {}

                    if not section.home_block_show_featured:
                        # articles should not be render twice if cover, (in cover and here)
                        top_articles_ids = [art.id for art in top_articles or []]
                        cover_article = context.get('cover_article')
                        if cover_article:
                            top_articles_ids.append(cover_article.id)
                        latest_kwargs['exclude_articles_ids'] = top_articles_ids

                    if (
                        self.article_type == 'OP'
                        and edition.publication.slug in settings.CORE_PUBLICATIONS_USE_ROOT_URL
                    ):
                        # special case for opinion articles
                        latest_kwargs['all_sections'] = True  # use all section if article_type is given
                        latest_kwargs['article_type'] = self.article_type
                        latest_kwargs['publications_ids'] = Publication.objects.filter(
                            slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL
                        ).values_list('id', flat=True)
                    else:
                        if self.article_type:
                            latest_kwargs['all_sections'] = True  # use all section if article_type is given
                            latest_kwargs['article_type'] = self.article_type
                        if not section.home_block_all_pubs:
                            latest_kwargs['publications_ids'] = [edition.publication.id]

                    articles = list(section.latest(**latest_kwargs))

            context.update({'articles': articles, 'section': section, 'edition': edition, 'art_count': len(articles)})
            try:
                result = loader.render_to_string(template, context.flatten())
            except TemplateDoesNotExist:
                pass

        return result


@register.simple_tag(takes_context=True)
def render_section(context, section_slug, article_type=None, top_index=None):
    return RenderSectionNode(context, section_slug, article_type, top_index).render(context)


@register.simple_tag(takes_context=True)
def publication_title(context):
    publication = context.get('publication')
    site_name, country_name = context.get('site').name, context.get('country_name')
    return (
        publication.html_title
        or (
            "%s | Noticias de %s y el mundo" % (site_name, country_name) if publication == context.get('default_pub')
            else "%s | %s | %s" % (publication.headline, site_name, country_name)
        )
    )


@register.simple_tag(takes_context=True)
def render_publication_row(context, publication_slug):
    try:
        publication = Publication.objects.get(slug=publication_slug)
    except Publication.DoesNotExist:
        return ''
    else:
        user = context.get('user')
        # if not public => render only if saff user
        if publication.public or user.is_staff:
            edition = get_current_edition(publication)
            if edition:
                flatten_ctx = context.flatten()
                flatten_ctx.update(
                    {
                        'publication_obj': publication,
                        'edition': edition, 'is_portada': True,  # both should be set
                        # force a blank first node because top_index should be > 0
                        'publication_destacados': [None] + edition.top_articles[:4],
                    }
                )
                if hasattr(user, 'subscriber') and user.subscriber.is_subscriber(publication.slug):
                    flatten_ctx['publication_obj_is_subscriber'] = True
                return loader.render_to_string(
                    getattr(settings, 'HOMEV3_PUBLICATION_ROW_TEMPLATE', 'publication_row.html'), flatten_ctx
                )
            else:
                return ''
        else:
            return ''


class RenderCategoryRowNode(Node):
    def __init__(self, category_slug, limit):
        self.category_slug = category_slug
        self.limit = limit

    def render(self, context):
        try:
            category = Category.objects.get(slug=self.category_slug)
        except Category.DoesNotExist:
            return ''
        else:
            latest_articles = category.latest_articles()[:self.limit]
            if latest_articles:
                flatten_ctx = context.flatten()
                flatten_ctx.update(
                    {
                        'category': category,
                        # both next entries should be set
                        'edition': get_current_edition(),
                        'is_portada': True,
                        # force a blank first node because top_index should be > 0
                        'category_destacados': [None] + latest_articles,
                    }
                )
                return loader.render_to_string(get_category_template(category.slug, "category_row"), flatten_ctx)
            else:
                return ''


class RenderArticlesSliderNode(Node):
    def __init__(self, context, type, slug, limit):
        self.type = type
        self.slug = slug
        self.limit = limit

    def render(self, context):
        if self.type == 'category':
            category = Category.objects.get(slug=self.slug)
            latest_articles = category.latest_articles()[:self.limit]
            flatten_ctx = context.flatten()
            flatten_ctx.update(
                {
                    'category': category,
                    'articles': latest_articles,
                    'edition': get_current_edition(),
                    'is_portada': True,
                    'slug': self.slug,
                    'name': category.name,
                    'description': category.description,
                    'art_count': len(latest_articles),
                }
            )
        else:
            # TODO: Implement this simple_tag for the templates section/apuntes-del-dia.html
            # TODO: and section/conexion-ganadera.html.
            return

        try:
            return loader.render_to_string(get_articles_slider_template(self.slug), flatten_ctx)
        except TemplateDoesNotExist:
            return loader.render_to_string('articles_slider.html', flatten_ctx)


@register.simple_tag(takes_context=True)
def render_publication_grid(context, data):
    publication, section_slug, flatten_ctx = data[0], data[3], context.flatten()
    try:
        featured_section = Section.objects.get(slug=section_slug) if section_slug else None
    except Section.DoesNotExist:
        featured_section = None
    flatten_ctx.update(
        {
            'publication': publication,
            'top_articles': data[1],
            'cover_article': data[2],
            "featured_section": featured_section,
        }
    )
    return loader.render_to_string(
        '%s/%s_grid.html' % (settings.HOMEV3_FEATURED_PUBLICATIONS_TEMPLATE_DIR, publication.slug), flatten_ctx
    )


@register.simple_tag(takes_context=True)
def render_category_row(context, category_slug, limit=getattr(settings, 'HOMEV3_CATEGORY_ROW_DEFAULT_LIMIT', 4)):
    return RenderCategoryRowNode(category_slug, limit).render(context)


@register.simple_tag(takes_context=True)
def render_category_slider(context, type, slug, limit=getattr(settings, 'HOMEV3_CATEGORY_ROW_DEFAULT_LIMIT', 4)):
    return RenderArticlesSliderNode(context, type, slug, limit).render(context)


@register.simple_tag(takes_context=True)
def render_cover(context):
    context.update({'is_cover': True})
    flatten_ctx = context.flatten()
    return loader.render_to_string(getattr(settings, 'HOMEV3_COVER_TEMPLATE', 'cover.html'), flatten_ctx)


class RenderHeaderNode(Node):
    def render(self, context, template_suffix):
        return loader.render_to_string('header%s.html' % template_suffix, context.flatten())


@register.simple_tag(takes_context=True)
def render_header(context, template_suffix=''):
    render_header_module = getattr(settings, 'HOMEV3_RENDER_HEADER_MODULE', None)
    if render_header_module:
        RenderHeaderNodeClass = __import__(render_header_module, fromlist=['RenderHeaderNode']).RenderHeaderNode
    else:
        RenderHeaderNodeClass = RenderHeaderNode
    return RenderHeaderNodeClass().render(context, template_suffix)


@register.simple_tag(takes_context=True)
def login_next_url(context, default='/'):
    if context.get('is_portada'):
        publication = context.get('publication')
        if publication:
            return publication.get_absolute_url()
        else:
            category = context.get('category')
            if category:
                return category.get_absolute_url()
    return default
