# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

import re
from time import timezone
from datetime import datetime, tzinfo, timedelta
from dateutil import tz
from math import copysign
from os.path import join
import pytz
from pytz import country_timezones, country_names
import requests

from django.conf import settings
from django.template import Engine
from django.template.exceptions import TemplateDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.utils.deconstruct import deconstructible


class TZ(tzinfo):
    def utcoffset(self, dt):
        return timedelta(
            seconds=int(copysign(timezone, int(datetime.now(pytz.timezone(settings.TIME_ZONE)).strftime('%z'))))
        )


tz_obj = TZ()


def datetime_isoformat(dt):
    return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, 0, tz_obj).isoformat()


def datetime_timezone():
    local_tz, dt = tz.gettz(settings.TIME_ZONE), datetime.now()
    dt = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, 0, local_tz)
    timezone_countries = {
        timezone: country for country, timezones in country_timezones.items() for timezone in timezones
    }
    tz_name = dt.strftime('%Z')
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
        data='{"operationName":"updateStory","variables":{"input":{"id":%d,"story":{"url":"%s://%s%s"}'
        ',"clientMutationId":"url updated"}},"query":"mutation updateStory($input: UpdateStoryInput!)'
        '{updateStory(input:$input){story{id}}}"}' % (
            article_id, settings.URL_SCHEME, settings.SITE_DOMAIN, new_url_path),
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
