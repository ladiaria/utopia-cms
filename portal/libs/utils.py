# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str

from socket import error
from hashlib import md5
import re
import smtplib
from random import choices
from hashids import Hashids
from pymailcheck import split_email

from django.conf import settings
from django.db import IntegrityError
from django.db.models.query import QuerySet
from django.http import HttpResponseBadRequest

from tagging.models import Tag, TaggedItem

from core.models import Article


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
    return md5(hash_this.encode('utf-8')).hexdigest()


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


# TODO: check if the functions above this line are used, if not, remove.


def set_amp_cors_headers(request, response):
    try:
        amp_source_origin = request.GET['__amp_source_origin']
    except KeyError:
        return HttpResponseBadRequest()
    if request.headers.get('amp-same-origin') == 'true':
        access_control_allow_origin = amp_source_origin
    else:
        try:
            access_control_allow_origin = request.headers['origin']
        except KeyError:
            return HttpResponseBadRequest()
    amp_access_main_header_name = 'AMP-Access-Control-Allow-Source-Origin'
    response[amp_access_main_header_name] = amp_source_origin
    response['Access-Control-Allow-Origin'] = access_control_allow_origin
    response['Access-Control-Allow-Credentials'] = 'true'
    response['Access-Control-Expose-Headers'] = amp_access_main_header_name
    return response


def smtp_quit(smtp_servers):
    for smtp_conn in smtp_servers:
        if smtp_conn:
            try:
                smtp_conn.quit()
            except smtplib.SMTPServerDisconnected:
                pass


def smtp_connect(alternative=0):
    """
    Authenticate to SMTP (if any auth needed) and return the conn instance.
    If alternative > 0, connect to the alternative SMTP configured in setting list (1-indexed).
    """
    email_conf = {}
    if alternative:
        try:
            email_conf = getattr(settings, "EMAIL_ALTERNATIVE", [])[alternative - 1]
        except IndexError:
            pass
    else:
        for setting in ('HOST', 'PORT', 'HOST_USER', 'HOST_PASSWORD', 'USE_TLS'):
            email_conf[setting] = getattr(settings, 'EMAIL_' + setting, None)

    host, port = email_conf.get('HOST'), email_conf.get('PORT')
    try:
        s = smtplib.SMTP(host, port) if host and port else None
    except error:
        s = None
    if s and email_conf.get('USE_TLS'):
        s.starttls()
    if s and email_conf.get('HOST_USER'):
        try:
            s.login(email_conf.get('HOST_USER'), email_conf.get('HOST_PASSWORD'))
        except smtplib.SMTPException:
            pass
    return s


smtp_dom_not_allowed = [getattr(settings, "EMAIL_DOMAINS_NOT_ALLOWED", [])]

try:
    smtp_servers_weights = [settings.EMAIL_MAIN_SERVER_WEIGHT]
except AttributeError:
    # when using weights, all weights must be configured, otherwise they are ignored
    smtp_servers_weights = None

for email_conf in getattr(settings, "EMAIL_ALTERNATIVE", []):
    smtp_dom_not_allowed.append(email_conf.get("DOMAINS_NOT_ALLOWED", []))
    if smtp_servers_weights:
        try:
            smtp_servers_weights.append(email_conf["WEIGHT"])
        except KeyError:
            smtp_servers_weights = None


def smtp_server_choice(user_email, servers_available, force_ignore_weights=False, ignore_from_available=None):
    """
    This function will return the index to the (main server + alternative servers) list filtered by the availability
    list given, not using the one ignored (if such arg received), randomnly choosed to deliver the email given.
    TODO: choices are "fixed" for the same domain in the same delivery, then, to avoid unnecesary repeated calls to
          this function, a class can be written to fill a hashtable for caching those per-domain choices.
          The class instance will be created and used only in the delivery command.
          (Note that the servers availability can change in the same delivery execution, also be careful if
          "ignore_from_available" is not None)
    """
    email_domain, choices_data, weights = split_email(user_email)["domain"], [], None
    for alt_index, not_allowed in enumerate(smtp_dom_not_allowed):
        if servers_available[alt_index] and email_domain not in not_allowed and ignore_from_available != alt_index:
            choices_data.append(alt_index)
    if choices_data:
        if not force_ignore_weights and smtp_servers_weights:
            weights = [smtp_servers_weights[alt_index] for alt_index in choices_data]
        index_chosen = choices(choices_data, weights=weights)[0]
    else:
        index_chosen = None
    return index_chosen


def nl_serialize_multi(article_many, category, for_cover=False, dates=True):
    if type(article_many) in (QuerySet, list):
        return [
            (
                t[0].nl_serialize(t[1], category=category, dates=dates), t[1]
            ) if type(t) is tuple else t.nl_serialize(category=category, dates=dates) for t in article_many
        ]
    elif article_many:
        return article_many.nl_serialize(for_cover, category=category, dates=dates)


def decode_hashid(hashed_id):
    return Hashids(settings.HASHIDS_SALT, 32).decode(hashed_id)


def manage_tags(tag_to_update, tag_replacement, tags_to_replace):
    """
    Args example:
        tag_to_update : 'Mundial 2022'
        tag_replacement : 'Mundial Qatar 2022'
        tags_to_replace : ['Qatar 2022', 'Mundial Catar 2022', 'Mundial de Catar 2022', 'Catar 2022']
    """

    do_replacement, articles_to_replace = True, []
    # iterate over articles with the tag to update
    # if any article has another tag present in tags to replace, remove it
    for article in TaggedItem.objects.get_by_model(Article, Tag.objects.filter(name__iexact=tag_to_update)):
        taglist, replace = [t.strip() for t in article.tags.split(',')], True
        for t in taglist:
            if any((t.lower() == tr.lower() or t.lower() == '"%s"' % tr.lower()) for tr in tags_to_replace):
                replace = False
                print('I will remove tag "%s" in article %d with tags: %s' % (t, article.id, article.tags))
                tags = [tag for tag in taglist if tag.lower() != t.lower()]
                new_article_tags = '"%s"' % tags[0] if len(tags) == 1 else ', '.join(tags)
                article.tags = new_article_tags
                article.save()
                print('\tDone. article.tags now is: ' + new_article_tags)
                break
        if replace:
            print('I will replace tag %s in article %d which has tags: %s' % (tag_to_update, article.id, article.tags))
            articles_to_replace.append(article)
        else:
            do_replacement = False

    if not do_replacement:
        print('\nCall me again to fix any other multiple occurrences.')
    else:
        try:
            tag = Tag.objects.get(name__iexact=tag_to_update)
            print('\nI will now update the tag and do the replacement in those articles...')
            # update the tag
            tag.name = tag_replacement
            try:
                tag.save()
            except IntegrityError:
                # the tag_replacement already exist, add tag_to_update to tags_to_replace list
                tags_to_replace.append(tag_to_update)
            # do the replacement in the article's tag attribute
            for a in articles_to_replace:
                taglist = [t.strip() for t in a.tags.split(',')]
                if len(taglist) == 1:
                    a.tags = '"%s"' % tag_replacement
                else:
                    taglist[taglist.index(tag_to_update)] = tag_replacement
                    a.tags = ', '.join(taglist)
                a.save()
            print('Done.')
        except Tag.DoesNotExist:
            pass
        except Tag.MultipleObjectsReturned:
            # TODO: what to do here?
            print('More than one tag matching the tag name to update given, aborting.')
            return

        print('\nI will now replace the other tags in articles and remove each tag after that:\n')
        tags_to_replace_lowered = [t.lower() for t in tags_to_replace]
        for tagname in tags_to_replace:
            for tag in Tag.objects.filter(name__iexact=tagname):
                for article in TaggedItem.objects.get_by_model(Article, [tag]):
                    taglist = [t.strip() for t in article.tags.split(',')]
                    if len(taglist) == 1:
                        article.tags = '"%s"' % tag_replacement
                    else:
                        replaced = False
                        for idx, t in enumerate(taglist):
                            if t.lower() in tags_to_replace_lowered:
                                if replaced:
                                    taglist.pop(idx)
                                else:
                                    taglist[idx] = tag_replacement
                                    replaced = True
                        article.tags = '"%s"' % taglist[0] if len(taglist) == 1 else ', '.join(taglist)
                    article.save()
                    print('\tSaved article %d with tags attr = %s' % (article.id, article.tags))

                # remove the tag from bd
                if not TaggedItem.objects.filter(tag=tag).exists():
                    tag.delete()
                    print('\tTag "%s" removed.' % tag)
                else:
                    print('\tWARNING: Tag "%s" not removed, some taggeditems left for this tag.' % tag)
        print('Done.')
