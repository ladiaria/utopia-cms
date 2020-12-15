# -*- coding: utf-8 -*-
from core.models import Article
from forms import SearchForm
from models import get_query

from decorators import render_response

from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.views.decorators.cache import never_cache


to_response = render_response('search/templates/')


def _paginate(request, query, results_per_page=15):
    paginator = Paginator(query, results_per_page)

    try:
        page = int(request.GET.get('pagina', '1'))
    except (ValueError):
        page = 1

    try:
        lista = paginator.page(page)
    except (EmptyPage, InvalidPage):
        lista = paginator.page(paginator.num_pages)

    return lista, page


@never_cache
@to_response
def search(request, token=''):
    import re
    dre = re.compile(r'\w+[\w\s]+', re.UNICODE)
    search_form = SearchForm()
    if not token:
        if request.method == 'GET':
            get = request.GET.copy()
            if 'q' in get:
                search_form = SearchForm(get)
                if search_form.is_valid():
                    token = get.get('q', '')
                    token = ''.join(dre.findall(token))
    if token and len(token) > 2:
        articles_query = get_query(token, ['headline', 'body', 'deck', 'lead'])
        matches_query = Article.objects.filter(
            articles_query, is_published=True).order_by('-date_published')
        cont = matches_query.count()
        lista_resultados, page = _paginate(request, matches_query)
    else:
        token = ''
        cont = 0
        lista_resultados, page = _paginate(request, '')

    return 'search_results.html', \
        {'form': search_form, 'token': token,
         'listaresultados': lista_resultados, 'page': page,
         'cont': cont}
