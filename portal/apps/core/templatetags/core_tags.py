# -*- coding: utf-8 -*-
import random
import string
from builtins import str, range
from datetime import datetime, timedelta
from os.path import join

from hashids import Hashids
from content_settings.conf import content_settings

from django.conf import settings
from django.urls import reverse
from django.template import Library, Node, TemplateSyntaxError, Variable, loader
from django.template.defaultfilters import stringfilter, slugify
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import Truncator

from tagging.models import Tag, TaggedItem

from core.models import Article, ArticleCollection, Supplement, Category, Section
from core.forms import SendByEmailForm
from core.utils import datetime_timezone, get_app_template, get_related_article_type_limits


register = Library()
hashids = Hashids(settings.USER_HASHID_SALT, 32)


@register.simple_tag(takes_context=True)
def updatectx(context, **kwargs):
    """
    updates the context with kwargs dict
    """
    context.update(kwargs)
    return ""


@register.simple_tag(takes_context=True)
def published_articles(context, **kwargs):
    """
    Usage: {% published_articles field1=val1 field2__isnull=True ...
              limit=10 exclude_ctx_vars='some_article_list:4 cover_article:0 another_list:1' %}
    """
    limit = kwargs.pop("limit", None)
    exclude_ctx_vars = kwargs.pop("exclude_ctx_vars", None)
    articles = Article.published.filter(**kwargs)
    if exclude_ctx_vars:
        exclude_ids = []
        for var, head in [varhead.split(":") for varhead in exclude_ctx_vars.split()]:
            varval, hval = context.get(var), int(head)
            if not hval:
                exclude_id = getattr(varval, "id", None)
                if exclude_id:
                    exclude_ids.append(exclude_id)
            else:
                exclude_ids.extend([ivar.id for ivar in varval[:hval] if hasattr(ivar, "id")])
        articles = articles.exclude(id__in=exclude_ids)
    return articles[:limit] if limit else articles


def related_data_using_publication(publication, section, article, limit, title=None):
    if (
        publication
        and section.slug not in getattr(settings, 'CORE_SECTIONS_EXCLUDE_RELATED', ())
        and publication.slug not in getattr(settings, 'CORE_PUBLICATIONS_EXCLUDE_RELATED', ())
    ):
        # use the publication
        upd_dict = {
            'articles': section.latest_related_by_publication(publication.id, article.id, limit),
            'section': title or (
                publication.headline
                if publication.slug in getattr(settings, 'CORE_PUBLICATIONS_RELATED_USE_HEADLINE', ())
                else publication.name
            ),
        }
        if title:
            upd_dict['title_no_prefix'] = True
        return upd_dict


@register.simple_tag(takes_context=True)
def render_related(context, article, amp=False, publication_priority=None, title=None):

    if not settings.CORE_ENABLE_RELATED_ARTICLES:
        return ""

    section = context.get('section')
    if not section:
        return ''

    category, publication, upd_dict = section.category, context.get('publication'), None

    settings_publication_priority = getattr(settings, "CORE_RENDER_RELATED_PUBLICATION_PRIORITY", False)
    if publication_priority is None:
        publication_priority = settings_publication_priority
    related_default_limit = getattr(settings, 'CORE_RENDER_RELATED_DEFAULT_LIMIT', 4)

    if publication and publication_priority:
        # 1st: give priority to publication, if defined by settings
        upd_dict = related_data_using_publication(publication, section, article, related_default_limit, title)

    if not upd_dict:
        category_priority = getattr(settings, "CORE_CATEGORY_RELATED_CATEGORY_PRIORITY", False)
        category_related_limits = getattr(settings, 'CORE_CATEGORY_RELATED_USE_CATEGORY', {})
        related_article_type_limit = get_related_article_type_limits().get(article.type)

        # 2nd: use category, if it is priorized globally or by settings but giving priority to article type limits
        if category_priority or related_article_type_limit or (category and category.slug in category_related_limits):

            if category:
                related_limit = (
                    related_article_type_limit
                    or category_related_limits.get(category.slug, related_default_limit)
                    or related_default_limit
                )
                upd_dict = {
                    'articles': section.latest_related_by_category(category.id, article.id, related_limit),
                    'section': category.more_link_title or category.name,
                }

        if not upd_dict:
            # 3rd: A conditional category-priorized (only for the sections specified in the setting)
            use_category_skip_sections = getattr(settings, 'CORE_CATEGORY_RELATED_USE_CATEGORY_SKIPPING_SECTIONS', [])
            if use_category_skip_sections:
                article_categories = article.get_categories_slugs()
                for category_slug, section_slugs in use_category_skip_sections:
                    if category_slug in article_categories and section.slug not in section_slugs:
                        category = Category.objects.get(slug=category_slug)
                        related_limit = category_related_limits.get(category.slug, related_default_limit)
                        if related_limit:
                            upd_dict = {
                                'articles': section.latest_related_by_category(category.id, article.id, related_limit),
                                'section': category.name,
                            }
                            break

        # 4th, if still blank, now is the turn of the default behavior, use the section
        if not upd_dict:
            upd_dict = {'articles': section.latest_related(article.id, related_default_limit), 'section': section.name}

        if not (upd_dict or publication_priority):
            # 5th: use the publication now, if it was not prioritized in the 1st "call"
            # NOTE: if the pub was prioritized, we already know here that it returns nothing,
            #       that's why we only call it "again" only if we know that it was not prioritized.
            upd_dict = related_data_using_publication(publication, section, article, related_default_limit, title)

    upd_dict.update({'is_detail': False, 'amp': amp})
    flatten_ctx = context.flatten()
    flatten_ctx.update(upd_dict)
    return loader.render_to_string(get_app_template(join("article/related", slugify(section) + ".html")), flatten_ctx)


# Media select
class MediaSelectNode(Node):
    def __init__(self, name):
        self.name = name

    def render(self, context):
        medias = (
            {'id': 'I', 'name': 'Image'},
            {'id': 'A', 'name': 'Audio'},
            {'id': 'V', 'name': 'Video'},
        )
        select_html = loader.render_to_string(
            'core/templates/media_select.html', {'medias': medias, 'select_name': self.name}
        )
        return select_html


@register.tag
def media_select(parser, token):
    bits = token.contents.split()[2:]
    # No quiero las posiciones 0 y 1 porque son el nombre del tag y la keyword
    # "with" respectivamente.
    kwargs = {}
    for param in bits:
        key, val = [str(p) for p in param.split('=')]
        kwargs[key] = val.replace('"', '')
    return MediaSelectNode(**kwargs)


@register.simple_tag(takes_context=True)
def render_article_card(context, article, media, card_size, card_type=None, img_load_lazy=True):
    if not article:
        return ""

    if not card_size:
        card_size = article.header_display

    if not card_type:
        card_type = article.type

    card_display, template_try_to_override, template_override = None, False, None

    # WARN: template value assigned here may change in next if block. TODO: fix this anti-pattern.
    if card_size == "FW":
        template = "card_full.html"
    elif card_size == "FD":
        template, template_try_to_override = "card_full_detailed.html", True
    elif card_size == "FF":
        template, template_try_to_override = "card_big_new.html", True
        card_display = "horizontal"
    elif card_size == "BG":
        template = "card_big.html"
    elif card_size == "MD":
        template = "card_medium.html"
    elif card_size == "SM":
        template = "card_small.html"
        media = "none"
    elif card_size == "OC":
        template = "card_big.html"
    else:
        template = "card_medium.html"

    # WARN: again, template may change in next if block.
    if card_type == 'OP':
        card_display = "horizontal"
        template = "card_opinion.html"
    elif card_type == 'SU':
        template = "card_summary.html"

    if card_size == "FN":
        template, template_try_to_override = "article_card_new.html", True

    if template_try_to_override:
        template_override = get_app_template(join("article", template))

    # compute card_display if not already done
    if not card_display:
        if article.photo_render_allowed() and article.photo.extended.is_portrait:
            card_display = "horizontal"
        else:
            card_display = "vertical"

    flatten_ctx = context.flatten()
    flatten_ctx.update(
        {
            'article': article,
            'media': media,
            'card_size': card_size,
            'card_display': card_display,
            'card_type': card_type,
            'img_load_lazy': img_load_lazy,
        }
    )
    return loader.render_to_string(
        template_override or ('core/templates/%sarticle/%s' % ('amp/' if flatten_ctx.get("amp") else '', template)),
        flatten_ctx,
    )


# Render article media list con foto a la izquierda para mostrar en sidebar
class RenderArticleMediaNode(Node):
    def __init__(self, article=None, media=None):
        self.article = Variable(article)
        self.media = Variable(media)

    def render(self, context):
        article = self.article.resolve(context)
        if not article:
            return ''
        media = self.media.resolve(context)
        context.update({'articles': [article], 'media': media, 'separador': True})
        return loader.render_to_string(
            'core/templates/article/media-list.html', context=context.flatten(), request=context.request
        )


@register.tag
def render_article_media(parser, token):
    bits = token.contents.split()[2:]
    kwargs = {}
    for param in bits:
        key, val = [str(p) for p in param.split('=')]
        kwargs[key] = val.replace('"', '')
    return RenderArticleMediaNode(**kwargs)


class ArticlesByTypeNode(Node):
    def __init__(self, type, keyword, limit=0):
        if type.startswith('"'):
            self.type = type.strip('"')
        else:
            self.type = Variable(type)
        self.keyword = keyword
        try:
            self.limit = int(limit)
        except ValueError:
            self.limit = Variable(limit)

    def render(self, context):
        from string import upper

        if isinstance(self.type, Variable):
            type = getattr(Article, upper(self.type.resolve(context)))
        else:
            type = getattr(Article, upper(self.type))
        articles = Article.published.filter(type=type)
        if self.limit:
            articles = articles[: self.limit]
        context.update({self.keyword: articles})
        return ''


@register.tag
def get_articles_by_type(parser, token):
    """Usage:
    {% get_articles_by_type 10 "ombudsman" as article_list %}
    or
    {% get_articles_by_type "ombudsman" as article_list %}
    """

    bits = token.contents.split()
    limit = None
    if len(bits) == 4:
        type = bits[1]
        keyword = bits[3]
    elif len(bits) == 5:
        limit = bits[1]
        type = bits[2]
        keyword = bits[4]
    else:
        raise TemplateSyntaxError('Invalid syntax for %s' % bits[0])
    return ArticlesByTypeNode(type=type, keyword=keyword, limit=limit)


@register.simple_tag(takes_context=True)
def render_toolbar_for(context, toolbar_object):
    """
    Usage example: {% render_toolbar_for article %}
    """
    user = context.get('user')
    toolbar_template = user and get_app_template("article/toolbar.html")
    if toolbar_template and user.is_staff and isinstance(toolbar_object, Article):
        params = {'article': toolbar_object, 'is_detail': False}
        if context.get('is_cover'):
            edition = context.get('edition')
            if edition:
                params['featured_order'] = ', '.join(
                    str(tp) for tp in toolbar_object.articlerel_set.filter(
                        edition=edition, home_top=True
                    ).values_list('top_position', flat=True)
                )
        context.update(params)
        return loader.render_to_string(toolbar_template, context.flatten())
    return ''


@register.simple_tag
def get_category(category_slug):
    try:
        return Category.objects.get(slug=category_slug)
    except Category.DoesNotExist:
        pass


@register.simple_tag
def get_section(section_slug):
    try:
        return Section.objects.get(slug=section_slug)
    except Section.DoesNotExist:
        pass


@register.simple_tag
def render_supplements():
    supplements = Supplement.objects.all()[:2]
    return loader.render_to_string('core/templates/supplement_list.html', {'supplements': supplements})


@register.simple_tag(takes_context=True)
def publication_section(context, article, pub=None):
    """
    Returns the anchor tag with the atricle.publication_section using the publication given by parameter or:
    publication_obj or publication context variables as the publication argument (or default_pub if both are None).
    TODO: why default_pub as last option instead of the article's "main_pub"?
    """
    section = article.publication_section(
        pub or context.get('publication_obj') or context.get('publication') or context.get('default_pub')
    )
    if section:
        use_section_link = getattr(settings, 'CORE_ARTICLE_CARDS_SECTION_LINK', True)
        s_name = getattr(settings, "CORE_ARTICLE_CARDS_SECTION_NAME_OVERRIDES", {}).get(section.slug, section.name)
        if use_section_link:
            return '<a href="%s">%s</a>' % (section.get_absolute_url(), s_name)
        else:
            return '<span>%s</span>' % s_name
    else:
        return ''


@register.simple_tag(takes_context=True)
def render_hierarchy(context, article, force_use_links=False):
    """
    A "parent > child" two items hierarchy to be rendered as part of the article metadata, since an article can be
    published in many sections of many publications, this information may be adjusted to match as best as possible the
    context on which the article is part of. This function tries to do this automatically receiving the context.
    But also can be very customized by settings, that's why the code is quite big and has many if-branches, the above
    similar function publication_section, also helps here, is used when the most important object in the context is
    a Publication and render a hierarchy structure with a possible parent can result redundant.
    """
    publication, category = context.get("publication"), context.get("category")
    section = article.publication_section(publication) if publication else article.get_section(category)
    if section:
        use_section_link = (
            force_use_links in (True, "True") or getattr(settings, 'CORE_ARTICLE_CARDS_SECTION_LINK', True)
        )
        parent, use_parent_link = [], getattr(settings, 'CORE_ARTICLE_CARDS_PARENT_LINK', use_section_link)
        if section.category or category:
            allowed, parent_allow = getattr(settings, "CORE_CATEGORY_ALLOW_RENDER_HIERARCHY", ()), True
            # break with a return if no one of the categories is allowed
            if allowed and not any(c.slug in allowed for c in (section.category, category) if c):
                if publication:
                    return publication_section(context, article)
                parent_allow = False
            if parent_allow:
                # And now, give precedence to section's (only if allow)
                if use_parent_link:
                    parent.append(
                        reverse('home', kwargs={'domain_slug': (section.category or category).slug})
                    )
                parent.append(section.category or category)
        elif context.get("render_hierarchy", False):
            if use_parent_link and not (
                not article.main_section
                or article.main_section.edition.publication.slug
                in getattr(settings, 'CORE_HIERARCHY_USE_PUBLICATION', ())
            ):
                parent.append(
                    reverse('home', kwargs={'domain_slug': article.main_section.edition.publication.slug})
                )
            parent.append(article.main_section.edition.publication)
        else:
            return publication_section(context, article)
        s_name = getattr(settings, "CORE_ARTICLE_CARDS_SECTION_NAME_OVERRIDES", {}).get(section.slug, section.name)
        if use_section_link:
            child = '<a href="%s">%s</a>' % (section.get_absolute_url(), s_name)
        else:
            child = '<span>%s</span>' % s_name
        if parent:
            parent_html = ('<a href="%s">%s</a>' if use_parent_link else '<span>%s</span>') % tuple(parent)
            return '&nbsp;›&nbsp;'.join([parent_html, child])
        else:
            return child
    elif category:
        return ''
    else:
        return publication_section(context, article)


@register.simple_tag(takes_context=True)
def render_tagcover(context, tagname):
    try:
        tag = Tag.objects.get(name=tagname)
    except Tag.DoesNotExist:
        return ''
    articles = TaggedItem.objects.get_by_model(Article, tag).filter(is_published=True).exclude(type='OP')[:6]
    if articles:
        context.update({'tag_cover_article': articles[0], 'tag_destacados': articles[1:]})
        return loader.render_to_string('core/templates/tagcover.html', context.flatten())
    else:
        return ''


@register.simple_tag(takes_context=True)
def render_tagrow(context, tagname, article_type, articles_max=4):
    """
    Renders "rows" using "tagrow" template to show upto articles_max articles tagged with the tag tagname.
    """
    try:
        tag = Tag.objects.get(name=tagname)
    except Tag.DoesNotExist:
        return ''
    articles = TaggedItem.objects.get_by_model(Article, tag).filter(
        is_published=True, type=article_type
    )[:articles_max]
    if articles:
        flatten_ctx, result = context.flatten(), ""
        for i in range(0, len(articles), 4):
            flatten_ctx.update({'latest_articles': articles[i: i + 4]})
            result += loader.render_to_string('core/templates/tagrow.html', flatten_ctx)
        return mark_safe(result)
    else:
        return ''


@register.simple_tag(takes_context=True)
def render_collectionrow(context):
    """
    Renders a row with the latest 4 published collections for the publication or category assigned in the conext vars.
    """
    publication, filter_kwargs = context.get("publication"), {}
    if publication:
        filter_kwargs["main_section__edition__publication"] = publication
    else:
        category = context.get("category")
        if category:
            filter_kwargs["main_section__section__category"] = category
        else:
            return ""
    articles = ArticleCollection.published.filter(**filter_kwargs)
    if articles:
        flatten_ctx = context.flatten()
        flatten_ctx.update({'latest_articles': [a.article_ptr for a in articles[:4]]})
        return loader.render_to_string('core/templates/tagrow.html', flatten_ctx)
    else:
        return ''


@register.simple_tag
def section_name_in_publication_menu(publication, section):
    return getattr(settings, 'CORE_SECTIONS_NAME_IN_PUBLICATION_MENU', {}).get(
        (publication.slug, section.slug), section.name
    )


@register.simple_tag(takes_context=True)
def tags_joined(context):
    return ", ".join(str(tag).title() for tag in context.get("tags"))


@register.simple_tag(takes_context=True)
def title_joinparts(context, first_part, first_separator=" | ", append_sitename=True):
    result = first_separator.join([first_part, context.get('site').name]) if append_sitename else first_part
    if context.get("title_append_country"):
        result = " | ".join([result, context.get('country_name')])
    return result


@register.simple_tag(takes_context=True)
def category_title(context):
    category = context.get('category')
    return category.html_title or title_joinparts(context, "%s: noticias y artículos periodísticos" % category)


@register.simple_tag(takes_context=True)
def section_title(context):
    """
    We use a "getattr or get" because core.views.article.article_list loads a dict in the section ctx var.
    """
    section = context.get('section')
    custom_title = getattr(section, 'html_title', None)
    if custom_title:
        return custom_title
    first_part = "Artículos en " + getattr(
        section, 'name', section.get('name', "sección") if isinstance(section, dict) else "sección"
    )
    return title_joinparts(
        context, first_part, append_sitename=getattr(settings, "CORE_SECTION_DETAIL_TITLE_APPEND_SITENAME", True)
    )


@register.simple_tag(takes_context=True)
def category_nl_subscribe_box(context):
    """
    Renders the subscribe box for the article category, if proper conditions are met
    """
    # TODO: can be improved and even removed making some modifications in caller templates
    subscriber = getattr(context.get('user'), 'subscriber', None)
    subscriber_nls = subscriber.get_newsletters_slugs() if subscriber else []
    category = context.get('category')

    if category and category.has_newsletter:
        # article has category with nl
        if category.slug not in subscriber_nls:
            return loader.render_to_string('core/templates/article/subscribe_box_category.html', context.flatten())

    return ''


@register.simple_tag
def timezone_verbose():
    return datetime_timezone()


@register.simple_tag
def date_published_verbose(article, flat=False):
    """
    Use settings to control when and how the date should be rendered in article cards.
    """
    if not getattr(settings, 'CORE_ARTICLE_CARDS_DATE_PUBLISHED_ENABLED', True):
        return ''
    main_section_edition = article.main_section.edition if article.main_section else None
    if (
        not getattr(settings, 'CORE_ARTICLE_CARDS_DATE_PUBLISHED_ONLY_ROOT_PUBLICATIONS', False)
        or main_section_edition
        and main_section_edition.publication.slug in settings.CORE_PUBLICATIONS_USE_ROOT_URL
    ):
        now = timezone.now()
        today = now.date()
        publishing_hour, publishing_minute = [int(i) for i in settings.PUBLISHING_TIME.split(':')]
        publishing = timezone.make_aware(
            datetime(today.year, today.month, today.day, publishing_hour, publishing_minute)
        )
        if main_section_edition:
            hide_delta = getattr(settings, 'CORE_ARTICLE_CARDS_DATE_PUBLISHED_HIDE_DELTA', None)
            if hide_delta:
                if main_section_edition.date_published == today and now < publishing + timedelta(hours=hide_delta):
                    return ''
        # in addition to the settings above, we also admit changes in a custom way using a custom module:
        custom_module, custom_data = getattr(settings, 'CORE_ARTICLE_CARDS_DATE_PUBLISHED_CUSTOM_MODULE', None), None
        if custom_module:
            custom_data = __import__(
                custom_module, fromlist=['article_date_published_verbose']
            ).article_date_published_verbose(article, main_section_edition, today, now, publishing)
            # return empty string if the custom_data is not None but evaluates to False
            if custom_data is not None and not custom_data:
                return ''
        return (
            "%s%s" if flat else '%s<div class="ld-card__date">%s</div>'
        ) % (' - ' if article.has_byline() else '', custom_data or article.date_published_verbose())
    else:
        return ''


# Inclusion tags
@register.inclusion_tag("article/_send_by_email_form.html")
def send_by_email_form(user):
    return {"form": SendByEmailForm(), "user": user}


# Filters
def name_wrap(name):
    return loader.render_to_string('core/templates/byline.html', {'name': name})


@register.filter
@stringfilter
def initials(value, args=False):
    # TODO: not used, should be refactored without using "name_wrap"
    from django.template.defaultfilters import safe

    ret = ''
    names = value.split(', ')
    if not args:
        for name in names:
            ret += name_wrap(name)
    else:
        for name in names:
            full_name = name.split(' ')
            first = full_name[0][0].upper()
            second = full_name[1][0].upper()
            ret += name_wrap(first + second)
    return safe(ret)


@register.filter(name='anios')
def anios(last):
    return list(range(2009, last))


@register.filter(name='user_hashid')
def user_hashid(user_id):
    return hashids.encode(user_id)


@register.filter
def truncatehtml(string, length):
    truncator = Truncator(string)
    return truncator.words(length, html=True)


truncatehtml.is_safe = True


@register.filter
def truncatehtml_chars(string, length):
    truncator = Truncator(string)
    return truncator.chars(length, html=True)


truncatehtml_chars.is_safe = True


@register.simple_tag(takes_context=True)
def social_profile_link(context, network):
    publication = context.get('publication_obj') or context.get('publication') or context.get('default_pub')
    publication_slug = publication.slug if publication else settings.DEFAULT_PUB
    if publication_slug:
        for profile in content_settings.SOCIAL_PROFILES.get(publication_slug, []):
            properties = profile.get(network)
            if properties:
                href = properties.get("href")
                if href:
                    return href
    return ""


@register.simple_tag
def randomgen():
    """
    Returns a 16 char length random string starting with a letter
    """
    return (
        random.choice(string.ascii_letters)
        + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))
    )
