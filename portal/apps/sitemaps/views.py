
from builtins import range

from django.urls import reverse
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.http import Http404
from django.contrib.sites.shortcuts import get_current_site
from django.template.response import TemplateResponse
from django.views.decorators.cache import cache_page

from .sitemaps import ArticleSitemap, ArticleNewsSitemap, ArticleNews48hsSitemap


# Cache TTLs (seconds) per sitemap section. As a news site we want freshly
# published articles to be crawlable quickly, so the Google News sitemap
# (news_48hs) gets a short TTL, while the full historical "articles" sitemap is
# expensive to build and rarely needs to change, so it gets a long one.
SITEMAP_CACHE_TTL = {
    'news_48hs': 5 * 60,
    # news_sitemap is the full Google News catalog (~100 pages, capped at 1000
    # URLs/page by Google News), so we can't reduce its page count. A shorter
    # TTL would only cause more regenerations as crawlers slowly walk the pages,
    # with no freshness benefit (new articles surface via news_48hs). Kept at 1h
    # to match production — no improvement here, but no regression either.
    'news_sitemap': 60 * 60,
    'articles': 6 * 60 * 60,
}
# Default for the index and any unforeseen section.
DEFAULT_SITEMAP_CACHE_TTL = 60 * 60


def index(
    request,
    template_name='sitemap_index.xml',
    mimetype='application/xml',
    sitemap_url_name='django.contrib.sitemaps.views.sitemap',
):
    # The index references the per-section sitemaps (and their page counts), so
    # cache it for as long as the freshest section it lists, otherwise a new
    # news article could be published without the index advertising its page.
    return _index(request, template_name, mimetype, sitemap_url_name)


@cache_page(min(SITEMAP_CACHE_TTL.values()))
def _index(request, template_name, mimetype, sitemap_url_name):

    sitemaps = {'news_48hs': ArticleNews48hsSitemap, 'articles': ArticleSitemap, 'news_sitemap': ArticleNewsSitemap}
    req_site, req_protocol, sites = get_current_site(request), 'https' if request.is_secure() else 'http', []

    for section, site in list(sitemaps.items()):
        if callable(site):
            site = site()
        protocol = req_protocol if site.protocol is None else site.protocol
        sitemap_url = reverse(sitemap_url_name, kwargs={'section': section})
        absolute_url = '%s://%s%s' % (protocol, req_site.domain, sitemap_url)
        sites.append({"location": absolute_url})
        for page in range(2, site.paginator.num_pages + 1):
            sites.append({"location": '%s?p=%s' % (absolute_url, page)})

    return TemplateResponse(request, template_name, {'sitemaps': sites}, content_type=mimetype)


def sitemap(request, section=None, template_name='sitemap.xml', mimetype='application/xml'):
    # Pick the cache TTL per section so the Google News sitemap stays fresh
    # while the heavy full-articles sitemap is cached for much longer. The
    # decorator is applied at call time because the TTL depends on `section`.
    ttl = SITEMAP_CACHE_TTL.get(section, DEFAULT_SITEMAP_CACHE_TTL)
    return cache_page(ttl)(_sitemap)(request, section, template_name, mimetype)


def _sitemap(request, section=None, template_name='sitemap.xml', mimetype='application/xml'):

    sitemaps = {'articles': ArticleSitemap, 'news_sitemap': ArticleNewsSitemap, 'news_48hs': ArticleNews48hsSitemap}
    req_site, req_protocol = get_current_site(request), 'https' if request.is_secure() else 'http'

    if section is not None:
        if section not in sitemaps:
            raise Http404("No sitemap available for section: %r" % section)
        maps = [sitemaps[section]]
    else:
        maps = list(sitemaps.values())
    page = request.GET.get("p", 1)

    urls = []
    for site in maps:
        try:
            if callable(site):
                site = site()

            if section == 'news_48hs':
                page_obj = site.paginator.page(page)
                objs = page_obj.object_list
                urls.extend([site.news_url_info(obj, req_site, req_protocol) for obj in objs])
            else:
                urls.extend(site.get_urls(page=page, site=req_site, protocol=req_protocol))
        except EmptyPage:
            raise Http404("Page %s empty" % page)
        except PageNotAnInteger:
            raise Http404("No page '%s'" % page)

    return TemplateResponse(request, template_name, {'urlset': urls}, content_type=mimetype)
