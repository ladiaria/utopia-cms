"""
Iterates over photologue's URL patterns and replaces Archive views with paginated versions to avoid loading all at once
and prevent system crashes.
"""
from functools import wraps

import photologue.urls as photologue_urls

from django.conf import settings
from django.http import Http404
from django.urls import path, re_path
from django.urls.resolvers import RoutePattern, URLPattern


app_name = photologue_urls.app_name


def _staff_only(callback):
    """Wrap a view so non-staff users get a 404 (public photologue pages disabled)."""
    @wraps(callback)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise Http404()
        return callback(request, *args, **kwargs)
    return wrapper


def _maybe_restrict(p):
    """When PHOTOLOGUE_RESTRICT_PUBLIC_PAGES is on, make every photologue page staff-only.

    The URL patterns are kept (so reverse() and Photo.get_absolute_url keep working); only the view
    callback is wrapped to raise Http404 for the public.
    """
    if not getattr(settings, "PHOTOLOGUE_RESTRICT_PUBLIC_PAGES", False):
        return p
    if not isinstance(p, URLPattern):
        return p
    return URLPattern(p.pattern, _staff_only(p.callback), p.default_args, p.name)


def get_pl_view_kwargs(photologue_template, **extra):
    """Return kwargs for paginated photologue archive views."""
    photos_paginate_by = getattr(settings, "PHOTOLOGUE_LADIARIA_PHOTOS_PAGINATE_BY", 28)
    return {
        'paginate_by': 10 if "gallery" in photologue_template else photos_paginate_by,
        'template_name': 'photologue_ladiaria/paginated_archive.html',
        'extra_context': {'photologue_template': photologue_template},
        **extra,
    }


def _template_for_archive_view(view_class):
    """Ask the view class for its default template (delegates to get_template_names)."""
    instance = view_class(object_list=view_class.queryset)
    return instance.get_template_names()[-1]


def _build_urlpatterns():
    """Build urlpatterns from photologue, replacing Archive views with paginated ones."""
    result = []
    for p in photologue_urls.urlpatterns:
        if not isinstance(p, URLPattern):
            result.append(p)
            continue
        view_class = getattr(p.callback, 'view_class', None)
        if view_class is None or 'Archive' not in view_class.__name__:
            result.append(p)
            continue
        photologue_template = _template_for_archive_view(view_class)
        view_initkwargs = getattr(p.callback, 'view_initkwargs', {})
        callback = view_class.as_view(**get_pl_view_kwargs(photologue_template, **view_initkwargs))
        pattern_obj = p.pattern
        if isinstance(pattern_obj, RoutePattern):
            new_p = path(pattern_obj._route, callback, name=p.name)
        else:
            new_p = re_path(pattern_obj._regex, callback, name=p.name)
        result.append(new_p)
    return [_maybe_restrict(p) for p in result]


urlpatterns = _build_urlpatterns()
