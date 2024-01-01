# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
import json
from datetime import date
from pydoc import locate

from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect, HttpResponseRedirect, Http404
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template import Engine, TemplateDoesNotExist
from django.shortcuts import get_object_or_404, render
from django.contrib.sites.models import Site
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse

from core.models import Edition, Publication, Article, Section


@never_cache
def section_detail(request, section_slug, tag=None, year=None, month=None, day=None):  # TODO: review the tag argument

    # removed or changed sections redirects by settings
    if section_slug in getattr(settings, 'CORE_SECTION_REDIRECT', {}):
        target_section_slug = settings.CORE_SECTION_REDIRECT[section_slug]
        if target_section_slug.startswith('/'):
            # support for a "direct path" redirect
            return HttpResponsePermanentRedirect(target_section_slug)
        reverse_kwargs = {'section_slug': target_section_slug}
        for arg, val in list({'tag': tag, 'year': year, 'month': month, 'day': day}.items()):
            if val:
                reverse_kwargs[arg] = val
        return HttpResponsePermanentRedirect(reverse('section_detail', kwargs=reverse_kwargs))

    section = get_object_or_404(Section, slug=section_slug)

    context, edition, articles, page = {'section': section}, None, None, request.GET.get('pagina')

    if section.meta_description:
        context['site_description'] = section.meta_description
    else:
        context['site_description'] = "Un listado de artículos, noticias y entrevistas sobre %s" % section
        if section.category:
            context['site_description'] += " dentro del área %s de %s" % (
                section.category,
                Site.objects.get_current().name,
            )
        context['site_description'] += "."

    custom_ctx_modname, custom_ctx_function = getattr(settings, 'CORE_SECTION_DETAIL_CUSTOM_CTX_MODULE', None), None
    if custom_ctx_modname:
        custom_ctx_function = getattr(locate(custom_ctx_modname), section_slug.replace("-", "_"), custom_ctx_function)
    if custom_ctx_function:
        custom_ctx_function(context)
        publication = None
    elif section_slug in getattr(settings, 'CORE_SECTIONS_DETAIL_USE_CATEGORY', ()):
        articles, publication = section.category.articles(), None
    else:
        if section.publications.exists():
            items = getattr(settings, 'CORE_SECTION_MAIN_PUBLICATION', {}).items()
            p = next((k for k, v in items if section_slug in v), '')
            publication = p and section.publications.filter(slug=p).first() or section.publications.all()[0]
        else:
            publication = get_object_or_404(Publication, slug=settings.DEFAULT_PUB)

        if year and month and day:
            date_published = date(int(year), int(month), int(day))
            edition = get_object_or_404(Edition, date_published=date_published, publication=publication)
            articles = edition.get_articles_in_section(section)
        else:
            articles = list(
                Article.objects.raw(
                    # TODO: "is_published" notion should be the same used in core.managers.get_published_kwargs
                    """
                    SELECT DISTINCT(id) FROM (
                        SELECT a.id,a.date_published
                        FROM core_article a JOIN core_articlerel ar ON a.id=ar.article_id
                        WHERE a.is_published AND ar.section_id=%d
                        UNION
                        SELECT id,date_published FROM core_article WHERE is_published AND id IN (
                            SELECT cr.article_id
                            FROM core_articlecollectionrelated cr
                                JOIN core_articlecollection c ON cr.collection_id=c.article_ptr_id
                                JOIN core_article a ON c.article_ptr_id=a.id
                                JOIN core_articlerel ar ON ar.id=a.main_section_id
                            WHERE c.traversal_categorization AND ar.section_id=%d AND a.is_published
                        )
                    ) AS foo
                    ORDER BY date_published DESC""" % (section.id, section.id)
                )
            )

        context['publication_use_headline'] = \
            publication.slug in getattr(settings, 'CORE_PUBLICATIONS_SECTION_DETAIL_USE_HEADLINE', ())

    context["publication"] = publication
    if not custom_ctx_function:
        paginator = Paginator(articles, 10)
        try:
            articles = paginator.page(page)
        except PageNotAnInteger:
            articles = paginator.page(1)
        except EmptyPage:
            articles = paginator.page(paginator.num_pages)
        context["articles"] = articles

    template = "core/templates/section/detail.html"
    # custom template support
    template_dir = getattr(settings, "CORE_SECTION_TEMPLATE_DIR", None)
    if template_dir:
        template_try = '%s/%s.html' % (template_dir, section_slug)
        template_engine = Engine.get_default()
        try:
            template_engine.get_template(template_try)
        except TemplateDoesNotExist:
            template_try = '%s/detail.html' % template_dir
            try:
                template_engine.get_template(template_try)
            except TemplateDoesNotExist:
                pass
            else:
                template = template_try
        else:
            template = template_try

    return render(request, template, context)


@never_cache
def latest_article(request, section_slug):
    try:
        return HttpResponseRedirect(
            get_object_or_404(Section, slug=section_slug).latest_article()[0].get_absolute_url()
        )
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
    list_rutas = "Rutas seteadas actualmente <b>(para enviar PDF de la próxima edición)</b>:<br>"
    for item in items:
        list_rutas += str(item) + "<br>"

    if not ruta == "listar":
        encontrada = ruta in items
        if not encontrada:
            items.append(str(str(ruta)))
            fjson = open(settings.JSON_RUTASPDF_PATH, 'w')
            fjson.write(json.dumps(items))
            fjson.close()
            list_rutas += str(ruta) + "<br>"
        return HttpResponse(
            (
                "<strong><u>EXITO:</u></strong> Se enviará el PDF de la próxima edición <br>"
                if not encontrada
                else "<strong><u>ERROR:</u></strong> La ruta ya se encuentra en la lista <br>"
            )
            + "<br>"
            + list_rutas
        )
    return HttpResponse(list_rutas)
