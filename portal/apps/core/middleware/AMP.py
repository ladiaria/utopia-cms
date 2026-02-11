from django.http import HttpResponseForbidden
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin


class OnlyArticleDetail(MiddlewareMixin):
    """ Middleware to avoid using AMP in non article detail pages. """

    def process_request(self, request):
        # TODO: check when amp is ready to allow also the "authorization" and "pingback" requests
        # TODO: what happens if resolve raises 404?
        if getattr(request, "is_amp_detect", False) and resolve(request.path_info).url_name != 'article_detail':
            return HttpResponseForbidden()
