# -*- coding: utf-8 -*-
# la diaria 2020. Aníbal Pacheco.

from apps import signupwall_visitor_mdb

from signupwall.models import Visitor


if signupwall_visitor_mdb:
    inserted = 0
    for v in Visitor.objects.iterator():
        vdoc = {}
        for field in ('session_key', 'ip_address', 'user_agent', 'last_update'):
            vdoc[field] = getattr(v, field)
        if v.user:
            vdoc['user'] = v.user.id
        if v.paths_visited.exists():
            vdoc['paths_visited'] = list(v.paths_visited.values_list('path', flat=True))
        signupwall_visitor_mdb.posts.insert_one(vdoc)
        inserted += 1
        # v.delete()
        if inserted % 10000 == 0:
            print(inserted)
