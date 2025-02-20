# -*- coding: utf-8 -*-
from builtins import object

import re
from datetime import datetime
from os.path import join, dirname
from pytz import country_timezones, country_names
import requests

from django.conf import settings
from django.template import Engine
from django.template.exceptions import TemplateDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.utils.deconstruct import deconstructible
from django.utils.timezone import is_aware, make_aware, localtime

from thedaily import get_app_template as thedaily_get_app_template


article_slug_readonly = getattr(settings, "CORE_ARTICLE_SLUG_FIELD_READONLY", True)


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


def get_app_template(template):
    custom_template_mapped = getattr(settings, "CORE_CUSTOM_TEMPLATE_MAP", {}).get(template)
    if custom_template_mapped is not None:
        return custom_template_mapped
    customizable_fallbacks = ["article/related", "article/detail"]
    custom_dir = getattr(settings, "CORE_ARTICLE_DETAIL_TEMPLATE_DIR", None)
    if custom_dir:
        engine, template_try = Engine.get_default(), join(custom_dir, template)
        try:
            engine.get_template(template_try)
        except TemplateDoesNotExist:
            relative_dir = dirname(template)
            if relative_dir in customizable_fallbacks:
                template = get_app_template(relative_dir + ".html")
        else:
            template = template_try
    else:
        # when a fallback is set, it will be used allways for installations without custom templates
        relative_dir = dirname(template)
        if relative_dir in customizable_fallbacks:
            template = get_app_template(relative_dir + ".html")
    return template


def get_hard_paywall_template():
    return thedaily_get_app_template("hard_paywall.html")


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


def nl_template_name(publication_slug, default="newsletter/newsletter.html"):
    if publication_slug:
        template_dirs = [getattr(settings, "CORE_PUBLICATIONS_NL_TEMPLATE_DIR", "newsletter/publication")]
        if template_dirs[0]:
            template_dirs.append("")
        engine = Engine.get_default()
        for base_dir in template_dirs:
            template_try = join(base_dir, '%s.html' % publication_slug)
            try:
                engine.get_template(template_try)
                return template_try
            except TemplateDoesNotExist:
                pass
    return default


def get_nl_featured_article_id():
    return getattr(settings, 'NEWSLETTER_FEATURED_ARTICLE', None)


def serialize_wrapper(article_or_list, publication, for_cover=False, dates=True):
    if isinstance(article_or_list, list):
        return [
            (
                t[0].nl_serialize(t[1], publication, dates=dates), t[1]
            ) if isinstance(t, tuple)
            else t.nl_serialize(publication=publication, for_cover=for_cover, dates=dates) for t in article_or_list
        ]
    elif article_or_list:
        return article_or_list.nl_serialize(for_cover, publication, dates=dates)


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
    """
    # TODO: run the test function defined after this function to see errors when input is html, fix them
    # TODO: use compiled regex
    Replace straight double quotes (") with curly double quotes ("") in the given string.

    Handles special cases for:
    - HTML tags (preserves quotes inside tags)
    - Spanish language characters and punctuation (¿¡ÑÁÉÍÓÚñáéíóú)

    Args:
        value (str): Input string containing straight quotes

    Returns:
        str: String with appropriate curly quotes substituted
    """
    value = re.sub(r"(?![^<>]*>)(\")\b", "“", value)
    value = re.sub(r"\b(?![^<>]*>)(\")", "”", value)
    value = re.sub(r"\"(?=[¿¡‘'\(\[ÑÁÉÍÓÚñáéíóú])", "“", value)
    value = re.sub(r"(?<=[\?\!’'\)ÑÁÉÍÓÚñáéíóú\.\%\]])\"", "”", value)
    return value


def test_smart_quotes():
    """Test cases where smart_quotes change/unchange the input"""
    test_cases = [
        # tuples of cases with 2 elements, first should be changed, second not
        # Basic quote replacement
        ('This is a "quote"', 'This is a <a href="quote">'),

        # Quote before Spanish characters
        ('"ítem!"', 'This is a <a href="item" title="ítem!">ítem!</a>'),

        # Quote after Spanish characters
        ('surubí"', 'surubí<a href="surubi" title="surubí">surubí</a>'),

        # Quote with punctuation
        ('Something?"', '<a href="something" title="Something?">Something?</a>'),

        # Multiple quotes
        ('He said "hello" and "goodbye"', 'He said <a href="hello" title="hello">hello</a> and <a href="goodbye">'),
    ]

    for to_be_changed, to_be_unchanged in test_cases:
        result = smart_quotes(to_be_changed)
        if result == to_be_changed:
            print(f"❌ No change when expected: '{to_be_changed}'")
        else:
            print(f"✓ Changed: '{to_be_changed}' -> '{result}'")
        result = smart_quotes(to_be_unchanged)
        if result != to_be_unchanged:
            print(f"❌ changed when not expected: '{to_be_unchanged}' -> '{result}'")
        else:
            print(f"✓ Unchanged: '{to_be_unchanged}'")


if __name__ == "__main__":
    # Run tests
    test_smart_quotes()
