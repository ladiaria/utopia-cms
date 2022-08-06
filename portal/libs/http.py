from __future__ import unicode_literals

from django.http import HttpResponseRedirect

def http_response_redirect_param(request, url):
    count = 0
    for (key, item) in list(request.GET.items()):
        if count == 0:
            char = '?'
        else:
            char = '&'
        url += '%s%s=%s' % (char, key, item)
        count += 1

    return HttpResponseRedirect(url)
