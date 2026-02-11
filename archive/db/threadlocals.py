# deprecated, archived.
# threadlocals middleware, can be used to obtain current user.
from __future__ import unicode_literals

from django.utils.deprecation import MiddlewareMixin

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local


_thread_locals = local()


def get_current_user():
    return getattr(_thread_locals, 'user', None)


class ThreadLocals(MiddlewareMixin):
    """ Middleware that gets various objects from the request object and saves them in thread local storage. """
    def process_request(self, request):
        _thread_locals.user = getattr(request, 'user', None)
