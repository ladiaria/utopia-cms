# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from .memcached_status import view

def memcached_status(request):
    return view(request)
