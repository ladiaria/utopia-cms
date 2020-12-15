# -*- coding: utf-8 -*-
from libs.utils import remove_spaces, remove_shorttags


class SpacelessMiddleware(object):
    def process_response(self, request, response):
        import re

        re_admin = re.compile(r'/admin/')
        matches = re_admin.match(request.META.get('PATH_INFO', ''))
        if not matches:
            if 'text/html' in response['Content-Type']:
                response.content = remove_spaces(response.content)
                response.content = remove_shorttags(response.content)
        return response
