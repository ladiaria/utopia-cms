# -*- coding: utf-8 -*-
from django import http
from django.conf import settings
from django.shortcuts import render_to_response

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

    class Stats:
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
        hit_rate = 100 * stats.get_hits / stats.cmd_get
    except:
        hit_rate = 100
    return render_to_response('memcached/memcached_status.html', dict(
        stats=stats, hit_rate=hit_rate,
        time=datetime.datetime.now(), # server time
    ))
