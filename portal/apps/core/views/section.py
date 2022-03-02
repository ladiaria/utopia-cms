# -*- coding: utf-8 -*-

import json
from datetime import date

from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect, HttpResponseRedirect, Http404
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, render
from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse

from core.models import Edition, Publication, Article, Section


@never_cache
def section_detail(request, section_slug, tag=None, year=None, month=None, day=None):

    # removed or changed sections redirects by settings
    if section_slug in getattr(settings, 'CORE_SECTION_REDIRECT', {}):
        target_section_slug = settings.CORE_SECTION_REDIRECT[section_slug]
        if target_section_slug.startswith('/'):
            # support for a "direct path" redirect
            return HttpResponsePermanentRedirect(target_section_slug)
        reverse_kwargs = {'section_slug': target_section_slug}
        for arg, val in {'tag': tag, 'year': year, 'month': month, 'day': day}.items():
            if val:
                reverse_kwargs[arg] = val
        return HttpResponsePermanentRedirect(reverse('section_detail', kwargs=reverse_kwargs))

    section = get_object_or_404(Section, slug=section_slug)

    edition, articles, page = None, None, request.GET.get('pagina', 1)

    # support custom templates
    template = 'core/templates/section/detail.html'
    template_dir = getattr(settings, 'CORE_SECTION_TEMPLATE_DIR', None)
    if template_dir and section_slug in getattr(settings, 'CORE_SECTION_CUSTOM_TEMPLATES', ()):
        template = '%s/%s.html' % (template_dir, section_slug)

    if section_slug in getattr(settings, 'CORE_SECTIONS_DETAIL_USE_CATEGORY', ()):
        articles = section.category.articles()
        paginator = Paginator(articles, 10)

        try:
            articles = paginator.page(page)
        except PageNotAnInteger:
            articles = paginator.page(1)
        except EmptyPage:
            articles = paginator.page(paginator.num_pages)

        return render(request, template, {'section': section, 'articles': articles, 'publication': None})

    # TODO: implement a way to mark one publication as the main publication for the section
    publication = section.publications.exists() and section.publications.all()[0] or \
        get_object_or_404(Publication, slug=settings.DEFAULT_PUB)

    if year and month and day:
        date_published = date(int(year), int(month), int(day))
        edition = get_object_or_404(Edition, date_published=date_published, publication=publication)
        articles = edition.get_articles_in_section(section)
    else:
        articles = list(Article.objects.raw("""
            SELECT a.id
            FROM core_article a JOIN core_articlerel ar ON a.id=ar.article_id
                JOIN core_edition e ON ar.edition_id=e.id
            WHERE ar.section_id=%d AND a.is_published
            GROUP BY a.id
            ORDER BY a.date_published DESC""" % section.id))

    paginator = Paginator(articles, 10)

    try:
        articles = paginator.page(page)
    except PageNotAnInteger:
        articles = paginator.page(1)
    except EmptyPage:
        articles = paginator.page(paginator.num_pages)

    return render(
        request,
        template,
        {
            'section': section,
            'articles': articles,
            'publication': publication,
            'publication_use_headline':
                publication.slug in getattr(settings, 'CORE_PUBLICATIONS_SECTION_DETAIL_USE_HEADLINE', ()),
        },
    )


@never_cache
def latest_article(request, section_slug):
    try:
        return HttpResponseRedirect(get_object_or_404(
            Section, slug=section_slug).latest_article()[0].get_absolute_url())
    except IndexError:
        raise Http404


@never_cache
@staff_member_required
def set_pdf_for_route(request, ruta=''):
    fjson = open(settings.JSON_RUTASPDF_PATH, 'a+')
    fjson.seek(0)
    items = []
    try:
        items = json.loads(fjson.read())
    except Exception:
        fjson.seek(0)
    fjson.close()
    list_rutas = u"Rutas seteadas actualmente<b> "
    u"(para enviar PDF de la próxima edición)</b>:<br>"
    for item in items:
        list_rutas += unicode(item) + u"<br>"

    if not ruta == "listar":
        encontrada = (ruta in items)
        if not encontrada:
            items.append(unicode(str(ruta)))
            fjson = open(settings.JSON_RUTASPDF_PATH, 'w')
            fjson.write(json.dumps(items))
            fjson.close()
            list_rutas += str(ruta) + "<br>"
        return HttpResponse((
            u"<strong><u>EXITO:</u></strong> Se enviará el PDF de la próxima "
            u"edición <br>" if not encontrada else
            u"<strong><u>ERROR:</u></strong> La ruta ya se encuentra en la "
            u"lista <br>") + u"<br>" + list_rutas)
    return HttpResponse(list_rutas)
