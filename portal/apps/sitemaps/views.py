
from builtins import range

from django.urls import reverse
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.http import Http404
from django.contrib.sites.shortcuts import get_current_site
from django.template.response import TemplateResponse

from .sitemaps import ArticleSitemap, ArticleNewsSitemap


def index(
    request,
    template_name='sitemap_index.xml',
    mimetype='application/xml',
    sitemap_url_name='django.contrib.sitemaps.views.sitemap',
):

    sitemaps = {'articles': ArticleSitemap, 'news_sitemap': ArticleNewsSitemap}
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

    sitemaps = {'articles': ArticleSitemap, 'news_sitemap': ArticleNewsSitemap}
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
            urls.extend(site.get_urls(page=page, site=req_site, protocol=req_protocol))
        except EmptyPage:
            raise Http404("Page %s empty" % page)
        except PageNotAnInteger:
            raise Http404("No page '%s'" % page)
    return TemplateResponse(request, template_name, {'urlset': urls}, content_type=mimetype)
