# -*- coding: utf-8 -*-
from os import path
from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE
from email.Utils import formatdate
from django.utils.deconstruct import deconstructible

import smtplib

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
import re


def get_pdf_pdf_upload_to(instance, filename):
    try:
        publication_slug = instance.publication.slug
    except AttributeError:
        publication_slug = instance.edition.publication.slug
    timestamp = instance.date_published.strftime('%Y%m%d')
    return path.join(
        'editions', publication_slug, timestamp, instance.get_pdf_filename())


def get_pdf_cover_upload_to(instance, filename):
    timestamp = instance.date_published.strftime('%Y%m%d')
    return path.join(
        'editions', instance.publication.slug, timestamp,
        instance.get_cover_filename())


def get_supplement_directory(instance):
    if instance.edition:
        date_strftime = instance.edition.date_published.strftime('%Y%m%d')
        directory = path.join('editions', date_strftime, 'supplement')
    else:
        date_strftime = instance.date_created.strftime('%Y%m%d')
        directory = path.join('supplements', date_strftime)
    return directory


def get_supplement_pdf_upload_to(instance, filename):
    directory = get_supplement_directory(instance)
    name = instance.slug.replace('-', '_')
    return path.join(directory, '%s.pdf' % name)


def get_pdfpage_pdf_upload_to(instance, filename):
    pass


def get_pdfpage_snapshot_upload_to(instance, filename):
    pass


def get_pdfpageimage_file_upload_to(instance, filename):
    pass


def add_punctuation(text):
    valid_chars = u'AÁBCDEÉFGHIÍJKLMNÑOÓPQRSTUÚVWXYZ' \
    u'aábcdeéfghiíjklmnñoópqrstuúvwxyz' \
    u'0123456789"'
    if text != '':
        if text[-1] in valid_chars:
            return u'%s.' % text
    return text


def send_mail(files, send_from='web-automatico@ladiaria.com.uy', send_to=['web-redaccion@ladiaria.com.uy'], subject='El PDF de hoy!', server='localhost'):
    assert type(send_to) == list
    assert type(files) == list
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    html = MIMEText('Se subió el siguiente PDF, corrobore que sea la edición de hoy!', 'html')
    msg.attach(html)

    for f in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(f,"rb").read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % path.basename(f))
        msg.attach(part)

    smtp = smtplib.SMTP(server, port=settings.EMAIL_PORT)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()


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
    value = re.sub(r"(?![^<>]*>)(\")\b", u"“", value)
    value = re.sub(r"\b(?![^<>]*>)(\")", u"”", value)
    value = re.sub(ur"\"(?=[¿¡\‘\'\(\[ÑÁÉÍÓÚñáéíóú])", u"“", value)
    value = re.sub(ur"(?<=[?!\’\'\)ÑÁÉÍÓÚñáéíóú\.\%\]])\"", u"”", value)
    return value
