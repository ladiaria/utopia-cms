from __future__ import unicode_literals
from django.http import HttpResponse


class HttpResponseTemporaryUnavailable(HttpResponse):
    status_code = 503
