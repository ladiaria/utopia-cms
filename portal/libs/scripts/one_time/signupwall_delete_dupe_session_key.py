from __future__ import unicode_literals
from signupwall.models import Visitor

# delete duplicate session_key rows in signupwall_visitor
for v in Visitor.objects.raw("""
        SELECT v1.id FROM signupwall_visitor v1
        WHERE EXISTS(
            SELECT id FROM signupwall_visitor
            WHERE session_key=v1.session_key AND v1.id>id)"""):
    v.delete()
