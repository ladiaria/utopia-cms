# -*- coding: utf-8 -*-
from django.template import Library, loader
from core.models import Section, Publication, Category, get_current_edition
from django.template.base import Node
from django.conf import settings


register = Library()

last_old_day = getattr(settings, 'LAST_OLD_DAY')


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


class RenderSectionNode(Node):
    def __init__(self, context, section_slug, article_type, top_index, article_type_template):
        self.section_slug = section_slug
        self.article_type = article_type
        self.top_index = top_index
        self.article_type_template = article_type_template

    def render(self, context):
        try:
            section = Section.objects.get(slug=self.section_slug)
        except Exception:
            section = None

        articles, edition = [], context.get('edition')

        if not edition:
            return u''

        top_articles = context.get('destacados')
        template = 'section%s.html' % (
            ('_' + self.article_type_template) if self.article_type_template
            else (('_' + self.article_type) if self.article_type else ''))

        if self.top_index:
            articles = top_articles[self.top_index:self.top_index + 4]
            template = 'section_row.html'

        elif section:

            if not section.in_home:

                return u''

            elif section.slug == u'apuntes-del-dia':

                articles = list(section.latest())

            else:

                latest_kwargs = {}

                if not section.home_block_show_featured:
                    # articles should not be render twice if cover, (in cover and here)
                    top_articles_ids = [art.id for art in top_articles or []]
                    cover_article = context.get('cover_article')
                    if cover_article:
                        top_articles_ids.append(cover_article.id)
                    latest_kwargs['exclude_articles_ids'] = top_articles_ids

                if self.article_type == 'OP' and edition.publication.slug in settings.CORE_PUBLICATIONS_USE_ROOT_URL:
                    # special case for opinion articles
                    latest_kwargs['all_sections'] = True  # use all section if article_type is given
                    latest_kwargs['article_type'] = self.article_type
                    latest_kwargs['publications_ids'] = Publication.objects.filter(
                        slug__in=settings.CORE_PUBLICATIONS_USE_ROOT_URL).values_list('id', flat=True)
                else:
                    if self.article_type:
                        latest_kwargs['all_sections'] = True  # use all section if article_type is given
                        latest_kwargs['article_type'] = self.article_type
                    if not section.home_block_all_pubs:
                        latest_kwargs['publications_ids'] = [edition.publication.id]

                articles = list(section.latest(**latest_kwargs))

        return loader.render_to_string(
            template, {'articles': articles, 'section': section, 'edition': edition, 'art_count': len(articles)},
            context_instance=context)


@register.simple_tag(takes_context=True)
def render_section(context, section_slug, article_type=None, top_index=None, article_type_template=None):
    return RenderSectionNode(context, section_slug, article_type, top_index, article_type_template).render(context)


class RenderPublicationRowNode(Node):
    def __init__(self, publication):
        self.publication = publication

    def render(self):
        edition = get_current_edition(publication=self.publication)
        return loader.render_to_string(getattr(settings, 'HOMEV3_PUBLICATION_ROW_TEMPLATE', 'publication_row.html'), {
            'publication': self.publication,
            'edition': edition, 'is_portada': True,  # both should be set
            # force a blank first node because top_index should be > 0
            'destacados': [None] + edition.top_articles[:4]})


@register.simple_tag(takes_context=True)
def render_publication_row(context, publication_slug):
    publication = Publication.objects.get(slug=publication_slug)
    # if not public => render only if saff user
    return RenderPublicationRowNode(publication).render() if publication.public or context['user'].is_staff else u''


class RenderCategoryRowNode(Node):
    def __init__(self, category_slug):
        self.category_slug = category_slug

    def render(self):
        try:
            category = Category.objects.get(slug=self.category_slug)
        except Category.DoesNotExist:
            return u''
        else:
            latest_articles = category.latest_articles()[:4]
            return loader.render_to_string('category_row.html', {
                'category': category,
                'edition': get_current_edition(), 'is_portada': True,  # both should be set
                # force a blank first node because top_index should be > 0
                'destacados': [None] + latest_articles}) if latest_articles else u''


@register.simple_tag()
def render_publication_grid(data):
    publication_slug = data[0]
    return loader.render_to_string(
        '%s/%s_grid.html' % (settings.HOMEV3_FEATURED_PUBLICATIONS_TEMPLATE_DIR, publication_slug), {
            'publication': Publication.objects.get(slug=publication_slug), 'top_articles': data[1],
            'cover_article': data[2]})


@register.simple_tag()
def render_category_row(category_slug):
    return RenderCategoryRowNode(category_slug).render()


@register.simple_tag(takes_context=True)
def render_cover(context):
    context.update({'is_cover': True})
    return loader.render_to_string(getattr(settings, 'HOMEV3_COVER_TEMPLATE', 'cover.html'), context)


class RenderHeaderNode(Node):
    def render(self, context, template_suffix):
        return loader.render_to_string('header%s.html' % template_suffix, context_instance=context)


@register.simple_tag(takes_context=True)
def render_header(context, template_suffix=''):
    render_header_module = getattr(settings, 'HOMEV3_RENDER_HEADER_MODULE', None)
    if render_header_module:
        RenderHeaderNodeClass = __import__(render_header_module, fromlist=['RenderHeaderNode']).RenderHeaderNode
    else:
        RenderHeaderNodeClass = RenderHeaderNode
    return RenderHeaderNodeClass().render(context, template_suffix)


@register.simple_tag(takes_context=True)
def login_next_url(context, default=u'/'):
    if context.get('is_portada'):
        publication = context.get('publication')
        if publication:
            return publication.get_absolute_url()
        else:
            category = context.get('category')
            if category:
                return category.get_absolute_url()
    return default
