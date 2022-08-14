# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from builtins import range
import re
from elasticsearch_dsl import Q

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.views.decorators.cache import never_cache

from core.models import Article

from decorators import render_response

from .forms import SearchForm
from .models import get_query
from .documents import ArticleDocument


to_response, dre, results_per_page = render_response('search/templates/'), re.compile(r'\w+[\w\s]+', re.UNICODE), 15


def _paginate(request, query):
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


def _page_results(request, s, total):
    try:
        page = int(request.GET.get('pagina'))
        # If page * results_per_page is greater than total , deliver last page of results.
        if page * results_per_page > total:
            from_ = total - results_per_page
            return s[from_:total]
        # deliver the resultset requested
        end = page * results_per_page
        from_ = abs(end - results_per_page)
        results = s[from_:end]
    except Exception:
        # If error occurred, deliver first page.
        results = s[:results_per_page]

    return results


@never_cache
@to_response
def search(request, token=''):
    search_form, page_results, elastic_search, elastic_match_phrase = SearchForm(), [], False, False

    if not token:
        if request.method == 'GET':
            get = request.GET.copy()
            if 'q' in get:
                search_form = SearchForm(get)
                if search_form.is_valid():
                    token = get.get('q', '')
                    token = ''.join(dre.findall(token))

    if token and len(token) > 2:

        if settings.ELASTICSEARCH_DSL:

            extra_kwargs = {}
            if settings.SEARCH_ELASTIC_MATCH_PHRASE:
                elastic_match_phrase = True
                extra_kwargs['type'] = 'phrase'
            elif settings.SEARCH_ELASTIC_USE_FUZZY:
                extra_kwargs['fuzziness'] = 'auto'

            s = ArticleDocument.search().query(
                Q('multi_match', query=token, fields=['headline^3', 'body', 'deck', 'lead'], **extra_kwargs)
                & Q("match", is_published=True)
                & Q("range", date_published={'lte': 'now/d'})
            )

            sort_arg = getattr(settings, 'SEARCH_ELASTIC_SORT_ARG', None)
            if sort_arg:
                s = s.sort(sort_arg)

            try:
                if request.GET.get('full') == u'1':
                    s = s.params(preserve_order=True)
                    matches_query = list(s.scan())
                else:
                    r = s.execute()
                    total = r.hits.total.value
                    # ES hits cannot be paginated with the same django Paginator class, we need to take the results
                    # for the page and simulate the dajngo pagination using a simple range list.
                    page_results, matches_query = _page_results(request, s, total), list(range(total))
            except Exception as exc:
                if settings.DEBUG:
                    print(u"search error: %s" % exc)
                search_form.add_error('q', u'No es posible realizar la búsqueda en este momento.')
                return 'search_results.html', {'form': search_form}
            cont, elastic_search = len(matches_query), True

        else:

            articles_query = get_query(token, ['headline', 'body', 'deck', 'lead'])
            matches_query = Article.published.filter(articles_query)
            cont = matches_query.count()

        results, page = _paginate(request, matches_query)

    else:

        token, cont = '', 0
        results, page = _paginate(request, '')

    return (
        'search_results.html',
        {
            'form': search_form,
            'token': token,
            'results': results,
            'page': page,
            'cont': cont,
            'page_results': page_results,
            'elastic_search': elastic_search,
            'elastic_match_phrase': elastic_match_phrase,
        },
    )
