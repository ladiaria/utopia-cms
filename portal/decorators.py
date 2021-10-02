from django.template import loader, Context, RequestContext, TemplateSyntaxError
from django.http import HttpResponse


def render_response(template_prefix=None, always_use_requestcontext=True):
    """
    Create a decorator which can be used as a shortcut to render templates to
    an HttpResponse.

    The decorated function must return either:
     * an HttpResponse object,
     * a string containing the template name (if doesn't start with '/' then
       will be combined with the template_prefix) or
     * a tuple comprising of:
         * a string or tuple containing the template name(s),
         * a dictionary to add to the Context or RequestContext and
         * (optionally) a list of context processors (if given, forces use of
           RequestContext).
         * (optionally) a headers dictionary to inject in the response

    Example usage (in a views module)::

        from projectname.renderer import render_response
        render_response = render_response('app_name/')     # Template dir.

        @render_response
        app_view(request):
            ...
            return 'app_view_template.htm', dict(object=object)
    """
    def renderer(func):
        def _dec(request, *args, **kwargs):
            response = func(request, *args, **kwargs)

            if isinstance(response, HttpResponse):
                return response
            elif isinstance(response, basestring):
                template_name = response
                namespace, context_processors, headers = {}, None, {}
            elif isinstance(response, (tuple, list)):
                len_tuple = len(response)
                if len_tuple == 2:
                    template_name, namespace = response
                    context_processors, headers = None, {}
                elif len_tuple == 3:
                    template_name, namespace, context_processors = response
                    headers = {}
                elif len_tuple == 4:
                    template_name, namespace, context_processors, headers = response
                else:
                    raise TemplateSyntaxError(
                        '%s.%s function did not return a parsable tuple' % (func.__module__, func.__name__)
                    )
            else:
                raise TemplateSyntaxError(
                    '%s.%s function did not provide a template name or HttpResponse object' % (
                        func.__module__, func.__name__
                    )
                )

            if always_use_requestcontext or context_processors is not None:
                context = RequestContext(request, namespace, context_processors)
            else:
                context = Context(namespace)

            if template_prefix:
                if isinstance(template_name, (list, tuple)):
                    template_name = map(correct_path, template_name)
                else:
                    template_name = correct_path(template_name)

            http_response = HttpResponse(
                loader.render_to_string(template_name, context=context.flatten(), request=context.request)
            )
            for header, header_value in headers.items():
                http_response[header] = header_value
            return http_response

        return _dec

    def correct_path(template_name):
        if template_name.startswith('/'):
            return template_name[1:]
        return '%s%s' % (template_prefix, template_name)

    return renderer


def decorate_if_no_staff(decorator):
    """
    Returns decorated view if user is not staff. Un-decorated otherwise
    taken from: https://stackoverflow.com/questions/7315862/django-prevent-caching-view-if-user-is-logged-in
    """

    def _decorator(view):

        decorated_view = decorator(view)  # This holds the view with decorator

        def _view(request, *args, **kwargs):

            if request.user.is_staff:     # If user is staff
                return view(request, *args, **kwargs)  # view without decorator
            else:
                return decorated_view(request, *args, **kwargs)  # view with decorator

        return _view

    return _decorator


def decorate_if_staff(decorator):
    """
    Returns decorated view if user is staff. Un-decorated otherwise
    (the inverse version of decorate_if_no_staff)
    """

    def _decorator(view):

        decorated_view = decorator(view)  # This holds the view with decorator

        def _view(request, *args, **kwargs):

            if request.user.is_staff:     # If user is staff
                return decorated_view(request, *args, **kwargs)  # view with decorator
            else:
                return view(request, *args, **kwargs)  # view without decorator

        return _view

    return _decorator
