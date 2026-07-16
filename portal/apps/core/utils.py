# -*- coding: utf-8 -*-
from builtins import object

import re
from datetime import datetime
from html import unescape
from os.path import join
from pytz import country_timezones, country_names
import requests

from django.conf import settings
from django.template import Engine
from django.template.exceptions import TemplateDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.utils.deconstruct import deconstructible
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.timezone import is_aware, make_aware, localtime


# Registration wall shown inline in the article. The email step (thedaily.views.registration_wall_email) resolves
# whether the submitted email already has an account and leaves the next step here, then redirects back to the
# article, which consumes it. The session and not the query string, so the email stays out of the referrer and the
# access logs and the article keeps a shareable url.
REGISTRATION_WALL_SESSION_KEY = "registration_wall"


def set_registration_wall_state(request, article, state, email):
    request.session[REGISTRATION_WALL_SESSION_KEY] = {
        "article_id": article.id, "state": state, "email": email
    }
    request.session.modified = True


def pop_registration_wall_state(request, article):
    """
    Return the (state, email) left for `article` by the email step, removing it from the session so a reload of the
    article starts the wall over. Returns (None, "") when there is nothing for this article.
    """
    stored = request.session.get(REGISTRATION_WALL_SESSION_KEY)
    # keyed by article so the state does not follow the reader into the next article
    if not stored or stored.get("article_id") != article.id:
        return None, ""
    del request.session[REGISTRATION_WALL_SESSION_KEY]
    request.session.modified = True
    return stored.get("state"), stored.get("email", "")


def truncate_body_words(body_html, words=None):
    """
    Return the first `words` words of a formatted article body, as the registration wall teaser, keeping the html
    tags balanced (Truncator with html=True closes any tag left open by the cut).

    The teaser is built here and not hidden with css on purpose: the registration wall must not ship the rest of the
    article in the page source, or the wall is trivially bypassed by reading it.
    """
    if words is None:
        words = getattr(settings, "SIGNUPWALL_TRUNCATE_ARTICLE_WORDS", 100)
    return mark_safe(Truncator(body_html).words(words, html=True))


# script and style are dropped with their content: a formatted body carries embed markup (instagram, youtube, ...)
# whose javascript source would otherwise become "words" of the excerpt.
REGISTRATION_WALL_TAIL_DROP_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.DOTALL | re.IGNORECASE)
# tags become a space instead of being deleted: django's strip_tags turns "<p>foo</p><p>bar</p>" into "foobar",
# which glues two words together and shifts every word after it.
REGISTRATION_WALL_TAIL_TAG_RE = re.compile(r"<[^>]+>")


def registration_wall_tail_words(body_html, start=None, words=None):
    """
    Return `words` words of a formatted article body starting at word `start`, as plain text, to be shown faded
    under the registration wall as a cue that the article goes on.

    Deliberately NOT the words that follow the teaser: text that continues across the wall reads as if the wall were
    an ad dropped mid-paragraph, and invites scrolling past it to keep reading. An excerpt from further down reads
    as an article that was cut.

    Plain text because it is decorative (unselectable and masked, see .article-body--registration-wall-tail). That
    also sidesteps balancing html tags across a cut that does not start at the beginning of the body, which
    Truncator cannot do: it only truncates a prefix.

    Not marked safe on purpose: the template escapes it, so markup that was literal text in the article stays
    literal here.

    Returns "" when the body does not reach `start`, and the tail is then not rendered at all. Falling back to the
    last words of the body instead would give away how the article ends.
    """
    if start is None:
        start = getattr(settings, "SIGNUPWALL_TRUNCATE_TAIL_START_WORD", 300)
    if words is None:
        words = getattr(settings, "SIGNUPWALL_TRUNCATE_TAIL_WORDS", 50)
    text = REGISTRATION_WALL_TAIL_DROP_RE.sub(" ", body_html)
    text = REGISTRATION_WALL_TAIL_TAG_RE.sub(" ", text)
    return " ".join(unescape(text).split()[start:start + words])


# Cache of computed cache-busting suffixes, keyed by static path. Filled once per worker process
# (at admin import time) so repeated calls do not re-hash the same file.
_VERSIONED_STATIC_CACHE = {}


def versioned_static(path):
    """Return the static URL for `path` with a ?v=<hash> cache-busting suffix derived from the
    file's current content.

    Why: nginx serves /static/ with `expires 1y` (Cache-Control: max-age=31536000), and the admin
    references its JS/CSS by a fixed, unversioned URL (e.g. js/homev2/article_admin.js). When such a
    file changes, the URL stays identical, so browsers and Cloudflare keep serving the year-old
    cached copy until someone manually purges the CDN and hard-refreshes. Appending a content hash
    makes the URL change whenever the file changes, busting both caches automatically on deploy.

    The returned value already starts with STATIC_URL ('/static/...'), so Django's Media.absolute_path
    emits it verbatim instead of running it through static()/URL-quoting (which would escape the '?').
    Falls back to the plain static URL if the source file can't be located.
    """
    import hashlib
    import os
    from django.contrib.staticfiles.finders import find
    from django.templatetags.static import static

    if path in _VERSIONED_STATIC_CACHE:
        return _VERSIONED_STATIC_CACHE[path]
    url = static(path)
    abs_path = find(path)
    if abs_path:
        try:
            with open(abs_path, "rb") as f:
                digest = hashlib.md5(f.read()).hexdigest()[:8]
            url = f"{url}?v={digest}"
        except OSError:
            # Unreadable file: degrade to the unversioned URL rather than breaking the admin.
            pass
    _VERSIONED_STATIC_CACHE[path] = url
    return url


def get_section_articles_sql(section_ids, excluded=[], limit=None):
    # pre: sections has at least 1 element
    # TODO: "is_published" notion should be the same used in core.managers.get_published_kwargs
    comparison = (
        ("=%d" % section_ids[0]) if len(section_ids) == 1 else (" IN (%s)" % ",".join(str(i) for i in section_ids))
    )
    excluded_statement = (" WHERE id NOT IN (%s)" % ",".join(str(i) for i in excluded)) if excluded else ""
    limit_statement = (" LIMIT %d" % limit) if limit else ""
    return """
    SELECT DISTINCT(id) FROM (
        SELECT a.id,a.date_published
        FROM core_article a JOIN core_articlerel ar ON a.id=ar.article_id
        WHERE a.is_published AND ar.section_id%s
        UNION
        SELECT id,date_published FROM core_article WHERE is_published AND id IN (
            SELECT cr.article_id
            FROM core_articlecollectionrelated cr
                JOIN core_articlecollection c ON cr.collection_id=c.article_ptr_id
                JOIN core_article a ON c.article_ptr_id=a.id
                JOIN core_articlerel ar ON ar.id=a.main_section_id
            WHERE c.traversal_categorization AND ar.section_id%s AND a.is_published
        )
    ) AS foo%s
    ORDER BY date_published DESC%s""" % (comparison, comparison, excluded_statement, limit_statement)


def datetime_isoformat(dt):
    if dt is None:
        return None
    dt = dt if is_aware(dt) else make_aware(dt)
    return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, 0, dt.tzinfo).isoformat()


def datetime_timezone():
    timezone_countries = {
        timezone: country for country, timezones in country_timezones.items() for timezone in timezones
    }
    tz_name = localtime().strftime('%Z')
    result = [tz_name if tz_name[0].isalpha() else 'GMT' + tz_name]
    tz_parts = settings.TIME_ZONE.split('/')
    if len(tz_parts) > 1:
        result.append(tz_parts[-1])
    try:
        result.append(country_names[timezone_countries[settings.TIME_ZONE]])
    except KeyError:
        pass
    return '(%s)' % ', '.join(result)


def get_pdf_pdf_upload_to(instance, filename):
    try:
        publication_slug = instance.publication.slug
    except AttributeError:
        publication_slug = instance.edition.publication.slug
    timestamp = instance.date_published.strftime('%Y%m%d')
    return join('editions', publication_slug, timestamp, instance.get_pdf_filename())


def get_pdf_cover_upload_to(instance, filename):
    timestamp = instance.date_published.strftime('%Y%m%d')
    return join('editions', instance.publication.slug, timestamp, instance.get_cover_filename())


def get_supplement_directory(instance):
    if instance.edition:
        date_strftime = instance.edition.date_published.strftime('%Y%m%d')
        directory = join('editions', date_strftime, 'supplement')
    else:
        date_strftime = instance.date_created.strftime('%Y%m%d')
        directory = join('supplements', date_strftime)
    return directory


def get_supplement_pdf_upload_to(instance, filename):
    directory = get_supplement_directory(instance)
    name = instance.slug.replace('-', '_')
    return join(directory, '%s.pdf' % name)


def get_pdfpage_pdf_upload_to(instance, filename):
    pass


def get_pdfpage_snapshot_upload_to(instance, filename):
    pass


def get_pdfpageimage_file_upload_to(instance, filename):
    pass


def get_category_template(category_slug, template_destination="detail"):
    default_dir = {"newsletter": "core/templates"}.get(template_destination, 'core/templates/category')
    custom_dir = getattr(settings, "CORE_CATEGORIES_TEMPLATE_DIR", None)
    destination_subdir = {"category_row": "row", "newsletter": "newsletter"}.get(template_destination, "")

    template = join(default_dir, destination_subdir, template_destination + ".html")
    if custom_dir:
        engine = Engine.get_default()
        # search by slug
        template_try = join(custom_dir, destination_subdir, category_slug + ".html")
        try:
            engine.get_template(template_try)
        except TemplateDoesNotExist:
            # then using "default" names instead of slugs
            template_try = join(custom_dir, destination_subdir, template_destination + ".html")
            try:
                engine.get_template(template_try)
            except TemplateDoesNotExist:
                pass
            else:
                template = template_try
        else:
            template = template_try
    # if custom dir is not defined, no search is needed
    return template



def add_punctuation(text):
    valid_chars = 'AÁBCDEÉFGHIÍJKLMNÑOÓPQRSTUÚVWXYZaábcdeéfghiíjklmnñoópqrstuúvwxyz0123456789"'
    if text != '':
        if text[-1] in valid_chars:
            return '%s.' % text
    return text


def update_article_url_in_coral_talk(article_id, new_url_path):
    # TODO: should be reviewed
    requests.post(
        settings.TALK_URL + 'api/graphql',
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + settings.TALK_API_TOKEN},
        data='{"operationName":"updateStory","variables":{"input":{"id":%d,"story":{"url":"%s"}'
        ',"clientMutationId":"url updated"}},"query":"mutation updateStory($input: UpdateStoryInput!)'
        '{updateStory(input:$input){story{id}}}"}' % (article_id, settings.SITE_URL_SD + new_url_path),
    ).json()['data']['updateStory']['story']


@deconstructible
class CT(object):

    __content_type_id__ = None

    def contenttype_id(self):
        if not self.__class__.__content_type_id__:
            self.__class__.__content_type_id__ = \
                ContentType.objects.get_for_model(self).pk
        return self.__class__.__content_type_id__

    def __eq__(self, other):
        return self.__content_type_id__ == other.__content_type_id__


def smart_quotes(value):
    value = re.sub(r"(?![^<>]*>)(\")\b", "“", value)
    value = re.sub(r"\b(?![^<>]*>)(\")", "”", value)
    value = re.sub("\"(?=[¿¡\‘\'\(\[ÑÁÉÍÓÚñáéíóú])", "“", value)
    value = re.sub("(?<=[?!\’\'\)ÑÁÉÍÓÚñáéíóú\.\%\]])\"", "”", value)
    return value


def ia_use_group(user):
    # Allow users in 'ia_use' group only
    return user.groups.filter(name='use_ia').exists()