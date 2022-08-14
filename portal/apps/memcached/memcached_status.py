# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import unicode_literals
from past.utils import old_div
from builtins import object
from django import http
from django.conf import settings
from django.shortcuts import render

import datetime, re

def view(request):

    try:
        import memcache
    except ImportError:
        raise http.Http404

    if not request.user.is_staff:
        raise http.Http404

    # get first memcached URI
    mre = re.compile("memcached://([.\w]+:\d+)")
    m = mre.match(settings.CACHE_BACKEND)
    if not m:
        raise http.Http404

    host = memcache._Host(m.group(1))
    host.connect()
    # TODO: Chequear si está corriendo el servidor y correr el script de carga
    # TODO: de ser necesario.
    host.send_cmd("stats")

    class Stats(object):
        pass

    stats = Stats()

    while 1:
        line = host.readline().split(None, 2)
        if line[0] == "END":
            break
        stat, key, value = line
        try:
            # convert to native type, if possible
            value = int(value)
            if key == "uptime":
                value = datetime.timedelta(seconds=value)
            elif key == "time":
                value = datetime.datetime.fromtimestamp(value)
        except ValueError:
            pass
        setattr(stats, key, value)

    host.close_socket()

    try:
        hit_rate = old_div(100 * stats.get_hits, stats.cmd_get)
    except:
        hit_rate = 100
    return render(request, 'memcached/memcached_status.html', dict(
        stats=stats, hit_rate=hit_rate,
        time=datetime.datetime.now(), # server time
    ))
