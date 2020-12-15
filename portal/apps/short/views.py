# -*- coding: UTF-8 -*-
from django.http import HttpResponseRedirect
from django.views.generic import DetailView
from django.views.decorators.cache import never_cache

from short.models import Url


class UrlDetailView(DetailView):
    model = Url


@never_cache
def redirect(request, url_id):
    return HttpResponseRedirect(Url.objects.get(id=url_id).url)
