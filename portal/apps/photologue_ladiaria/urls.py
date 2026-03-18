"""
Iterates over photologue's URL patterns and replaces Archive views with paginated versions to avoid loading all at once
and prevent system crashes.
"""
import photologue.urls as photologue_urls

from django.conf import settings
from django.urls import path, re_path
from django.urls.resolvers import RoutePattern, URLPattern


app_name = photologue_urls.app_name


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
    return result


urlpatterns = _build_urlpatterns()
