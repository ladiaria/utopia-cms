# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from shoutbox.models import Shout, get_last_shouts

from decorators import render_response

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse

to_response = render_response('shoutbox/templates/')

@login_required
def do_shout(request):
    if request.method == 'POST':
        post = request.POST.copy()
        if post.get('message'):
            shout = Shout()
            shout.user = request.user
            shout.message = post.get('message')
            shout.save()
        return HttpResponse('')
    else:
        raise Http404

@to_response
def shouts(request):
    from django.core.cache import cache

    if request.method == 'POST':
        shouts = cache.get('shouts', None)
        if not shouts:
            shouts = get_last_shouts()
            cache.set('shouts', shouts, 3600) # 1 hour
        return 'shouts.html', {'shouts': shouts}
    raise Http404
