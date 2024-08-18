# -*- coding: utf-8 -*-

from builtins import range
import re
from elasticsearch_dsl import Q

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.views.decorators.cache import never_cache

from core.models import Article

from decorators import render_response

from .forms import SearchForm
from .models import get_query
from .documents import ArticleDocument


to_response, dre, results_per_page = render_response('search/templates/'), re.compile(r'\w+[\w\s]+', re.UNICODE), 15


def _paginate(page, query, results_per_page=results_per_page):
    paginator = Paginator(query, results_per_page)
    try:
        lista = paginator.page(page)
    except PageNotAnInteger:
        lista = paginator.page(1)
    except (EmptyPage, InvalidPage):
        lista = paginator.page(paginator.num_pages)
    return lista


def _page_results(page, s, total, results_per_page=results_per_page):
    try:
        page, page_max = int(page), (total // results_per_page) + bool(total % results_per_page)
        # If page is greater than page_max, deliver last page of results.
        if page > page_max:
            page = page_max
        # deliver the resultset requested
        results = s[(page - 1) * results_per_page:total if page == page_max else (page * results_per_page)]
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

    page = request.GET.get("pagina")
    if token and len(token) > 2:

        if settings.ELASTICSEARCH_DSL:

            extra_kwargs = {}
            if settings.SEARCH_ELASTIC_MATCH_PHRASE:
                elastic_match_phrase = True
                extra_kwargs['type'] = 'phrase'
            elif settings.SEARCH_ELASTIC_USE_FUZZY:
                extra_kwargs['fuzziness'] = 'auto'

            s = ArticleDocument.search().query(
                Q(
                    'multi_match',
                    query=token,
                    fields=['unformatted_headline^3', 'unformatted_body', 'unformatted_deck', 'unformatted_lead'],
                    **extra_kwargs,
                )
                & Q("match", is_published=True)
                & Q("range", date_published={'lte': 'now/d'})
            )

            sort_arg = getattr(settings, 'SEARCH_ELASTIC_SORT_ARG', None)
            if sort_arg:
                s = s.sort(sort_arg)

            try:
                if request.GET.get('full') == '1':
                    # TODO: comment the purpose of this "full" parameter
                    s = s.params(preserve_order=True)
                    matches_query = list(s.scan())
                else:
                    r = s.execute()
                    total = r.hits.total.value
                    # ES hits cannot be paginated with the same django Paginator class, we need to take the results
                    # for the page and simulate the Django pagination using a simple range list.
                    page_results, matches_query = _page_results(page, s, total), list(range(total))
            except Exception as exc:
                if settings.DEBUG:
                    print("search error: %s" % exc)
                search_form.add_error('q', 'No es posible realizar la búsqueda en este momento.')
                return 'search_results.html', {'form': search_form}
            cont, elastic_search = len(matches_query), True

        else:

            articles_query = get_query(token, ['headline', 'body', 'deck', 'lead'])
            matches_query = Article.published.filter(articles_query)
            cont = matches_query.count()

        results = _paginate(page, matches_query)

    else:

        token, cont, results = '', 0, _paginate(page, '')

    return (
        'search_results.html',
        {
            'form': search_form,
            'token': token,
            'results': results,
            'cont': cont,
            'page_results': page_results,
            'elastic_search': elastic_search,
            'elastic_match_phrase': elastic_match_phrase,
        },
    )
