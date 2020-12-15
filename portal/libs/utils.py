# -*- coding: utf-8 -*-
import md5
import re
import smtplib

from django.conf import settings
from django.http import HttpResponseBadRequest


def remove_spaces(s):
    inline_tags = 'a|b|i|u|em|span|strong|sup|sub|tt|font|small|big'
    inlines_with_spaces = r'</(%s)>[\s\n\t]+<(%s)\b' % (
        inline_tags, inline_tags)

    re_inline = re.compile(inlines_with_spaces)
    s = re_inline.sub(r'</\1>&#preservespace;<\2', s)

    re_tags = re.compile(r'>[\n\s]+<')
    s = re_tags.sub('><', s)

    re_spaces = re.compile(r'\n\s+')
    s = re_spaces.sub('\n', s)

    re_to_space = re.compile(r'[\t\n\s]+')
    s = re_to_space.sub(' ', s)

    s = s.replace('&#preservespace;', ' ')

    return s


def remove_shorttags(s):
    return s.replace(' />', '>')


def next(request):
    next = '/'
    if 'next' in request.GET:
        next = request.GET.get('next', '/')
    elif 'next' in request.POST:
        next = request.POST.get('next', '/')
    # path = request.META.get('PATH_INFO', '/')
    if next.startswith('/usuarios'):
        next = '/'
    return next


def do_gonzo(*args, **kwargs):
    hash_this = ''
    for arg in args:
        hash_this += '%s$' % str(arg)
    for arg in kwargs:
        hash_this += '%s$' % str(kwargs.get(arg))
    hash_this += settings.SECRET_KEY
    return md5.md5(hash_this).hexdigest()


def md5file(filename):
    """
    Re-implementation of md5sum in python. Return the hex digest of a file
    without loading it all into memory.

    By Nick Craig-Wood <nick@craig-wood.com>
    """

    fh = open(filename)
    digest = md5.new()
    while 1:
        buf = fh.read(4096)
        if buf == "":
            break
        digest.update(buf)
    fh.close()
    return digest.hexdigest()


def set_amp_cors_headers(request, response):
    try:
        amp_source_origin = request.GET['__amp_source_origin']
    except KeyError:
        return HttpResponseBadRequest()
    if request.META.get('HTTP_AMP_SAME_ORIGIN') == 'true':
        access_control_allow_origin = amp_source_origin
    else:
        try:
            access_control_allow_origin = request.META['HTTP_ORIGIN']
        except KeyError:
            return HttpResponseBadRequest()
    amp_access_main_header_name = 'AMP-Access-Control-Allow-Source-Origin'
    response[amp_access_main_header_name] = amp_source_origin
    response['Access-Control-Allow-Origin'] = access_control_allow_origin
    response['Access-Control-Allow-Credentials'] = 'true'
    response['Access-Control-Expose-Headers'] = amp_access_main_header_name
    return response


def smtp_connect(alternative=False):
    """
    Authenticate to SMTP (if any auth needed) and return the conn instance.
    If alternative is True, connect to the alternative SMTP instead of the default.
    """
    email_conf = {}
    for setting in ('HOST', 'PORT', 'HOST_USER', 'HOST_PASSWORD'):
        email_conf[setting] = getattr(settings, ('EMAIL_%s' + setting) % ('ALTERNATIVE_' if alternative else ''), None)

    s = smtplib.SMTP(email_conf['HOST'], email_conf['PORT'])
    try:
        s.login(email_conf['HOST_USER'], email_conf['HOST_PASSWORD'])
    except smtplib.SMTPException:
        pass
    return s
