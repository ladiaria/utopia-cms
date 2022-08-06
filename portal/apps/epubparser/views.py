#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import str
from django.shortcuts import redirect
from django.template import RequestContext
import os, re
import ebooklib
from ebooklib import epub, utils
from bs4 import BeautifulSoup, Tag
from django.views.generic import ListView, FormView, View, DetailView
from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib import messages
from .models import EpubFile
from .forms import UploadEpubForm, EpubChangeSectionForm
import traceback
from lxml import etree
from lxml.etree import tostring
from core.models import Article, Section


class FileAddView(FormView):
    form_class = UploadEpubForm
    success_url = reverse_lazy('epub-home')
    template_name = "epubparser/templates/add_epub_parser.html"

    def form_valid(self, form):
        epub_section = form.cleaned_data['section']
        epub_file = form.cleaned_data['f']

        if str(epub_file).endswith('.epub'):
            form.save(commit=True)
            messages.success(self.request, 'Epub ingresado correctamente', fail_silently=True)
        else:
            messages.error(self.request, 'El archivo no es un EPUB')
        return super(FileAddView, self).form_valid(form)


class FileListView(ListView):
    model = EpubFile
    queryset = EpubFile.objects.order_by('-id')
    context_object_name = "files"
    template_name = "epubparser/templates/index_epub_parser.html"
    paginate_by = 5


class ParseView(DetailView):
    model = EpubFile
    context_object_name = "files"
    template_name = "epubparser/templates/index_epub_parser.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ParseView, self).get_context_data(**kwargs)
        epub_file = context['files'].f
        file = EpubFile.objects.get(f=epub_file)
        epub_section = file.section

        try:
            book = epub.read_epub(epub_file)
            for item in book.get_items():
                # - 9 es el codigo de tipo de archivo xhtml
                if (item.get_type() is 9):
                    content = item.get_body_content()

                    print(content)

                    #reemplazo los estilos con classes css del xhtml del epub
                    content = replace_style(content,
                                            '<span class="char-style-override-1">',
                                            '</span>', '<span>', '</span> ')

                    content = replace_style(content,
                                            '<span class="char-style-override-3">',
                                            '</span>', '_', '_')

                    content = replace_style(content,
                                            '<span class="Muy-destacado char-style-override-3">',
                                            '</span>', '', '')

                    content = replace_style(content,
                                            '<span class="Muy-destacado char-style-override-4">',
                                            '</span>', '', '')

                    content = replace_style(content,
                                            '<p class="Subt-tulo">',
                                            '</p>', '<p class="Normal">\nS>', '</p>')

                    content = replace_style(content,
                                            '<p class="Primer para-style-override-1">',
                                            '</p>', '<p class="Primer">', '</p>')

                    content = replace_style(content,
                                            '<span>', '</span>', ' ', ' ')


                    soup = BeautifulSoup(content, 'html.parser')

                    #cada subcuadro contiene un articulo
                    subcuadro_nota = soup('div', {'class': 'Subcuadro-nota'})

                    for e in subcuadro_nota:

                        tag = etree.fromstring(str(e))
                        titulo = ''.join(tag.xpath('//p[starts-with(@class, "T-tulo")]/text()'))
                        bajada = ''.join(tag.xpath('//p[@class="Bajada"]/text()'))
                        copete = ''.join(tag.xpath('//p[starts-with(@class, "Copete")]/text()'))
                        parrafos = '\n\n'.join(
                            tag.xpath('(//p[@class="Primer"]|//p[@class="Normal"]|//p[@class="Normal"]/span '
                                      '|//p[@class="Subt-tulo"]|//p[@class="Autor"])/text()'))

                        if titulo:
                            try:
                                article = Article(
                                    headline=titulo,
                                    deck=bajada,
                                    lead=copete,
                                    #home_lead=copete,
                                    body=parrafos,

                                )
                                article.save()
                                ar = Article.objects.get(id=article.id)
                                ar.sections.add(epub_section.id)
                                ar.save()

                                success_msg = 'Articulo generado correctamente: %s' % article.headline
                                messages.success(self.request, success_msg, fail_silently=True)

                            except:
                                traceback.print_exc()
                                messages.error(self.request, 'Hubo un error al procesar el archivo')
        except:
            traceback.print_exc()
            messages.error(self.request, 'Hubo un error al procesar el archivo')
       
       
        files = EpubFile.objects.order_by('-id')
        section = Section.objects.all()
        context['files'] = files
        context['section'] = section
        return context


class FileChangeView(DetailView):
    model = EpubFile
    context_object_name = "files"
    template_name = "epubparser/templates/change_epub_parser.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(FileChangeView, self).get_context_data(**kwargs)
        epub_file = context['files']
        sec = context['files'].section
        section = Section.objects.all()
        context['section'] = section
        context['files'] = epub_file

        changeForm = EpubChangeSectionForm()
        changeForm.f = epub_file
        changeForm.section = sec
        context['changeForm'] = changeForm

        return context


def changeSection(request):
    if request.method == 'POST':
        try:
            id_epub = request.POST.get('id_epub')
            sec = request.POST.get('section')
            epub = EpubFile.objects.get(id=id_epub)
            section = Section.objects.get(id=sec)
            epub.section = section
            epub.save()
        except:
            traceback.print_exc()
            messages.error(request, 'Debe seleccionar una SECCIÓN')
    return redirect(reverse('epub-home'))


def replace_style(content, tag_abre_style, tag_cierra_style, tag_change_style, tag_close_style):
    encontre = True
    while encontre:
        posicion_abre_span = content.find(tag_abre_style)
        #si no encuentra el span se va del loop
        if (posicion_abre_span == -1):
            encontre = False
        else:
            #posicion de cierre del span
            posicion_cierra_span = content.find(tag_cierra_style, posicion_abre_span)
            #reemplaza el proximo cierre de span por el cierre de em
            content = replace_at_position(content,tag_cierra_style, tag_close_style, posicion_cierra_span)
            #reemplaza la apertura del span por la apertura del em
            content = replace_at_position(content,tag_abre_style, tag_change_style, posicion_abre_span)

    return content


#reemplaza en la cadena total la cadena vieja por la cadena nueva
#la cadena vieja esta ubicada en la cadena_total en la posicion pos
def replace_at_position(cadena_total, cadena_vieja, cadena_nueva, pos):
    cadena_total = cadena_total[:pos] + cadena_nueva + cadena_total[pos+len(cadena_vieja):]
    return cadena_total
