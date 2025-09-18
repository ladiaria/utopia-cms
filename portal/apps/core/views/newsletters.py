from apps import bouncer_blocklisted
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from thedaily.utils import unsubscribed_newsletters, get_app_template


@never_cache
def index(request):
    """
    View to display and manage available newsletters for subscription.

    Args:
        request: HttpRequest object

    Returns:
        HttpResponse: Rendered template with the newsletter list
    """
    user = request.user
    subscriber = getattr(user, "subscriber", None)

    # Check if the user can have unsubscribed newsletters based on conditions
    user_can_subscribe = (
        user.is_authenticated
        and subscriber is not None
        and user.email
        and user.email not in bouncer_blocklisted
    )

    # If the user can subscribe, pass their data; otherwise pass False.
    unsubscribed_list = unsubscribed_newsletters(
        subscriber if user_can_subscribe else False, False
    )

    # Sort alphabetically by newsletter name
    try:
        unsubscribed_list = sorted(unsubscribed_list, key=lambda x: x.name.lower())
    except (AttributeError, TypeError):
        # Fallback: if there are issues with sorting, keep original list
        # AttributeError: when an object doesn't have 'name' attribute
        # TypeError: when 'name' exists but isn't a string (e.g.: None, 123, etc.)
        pass

    # Check if user just registered (from welcome URL parameter)
    show_welcome_buttons = request.GET.get('welcome') == '1'

    context = {
        "unsubscribed_newsletters": unsubscribed_list,
        "show_newsletters_pill": True,
        "show_welcome_buttons": show_welcome_buttons,
    }

    # If the user doesn't meet the conditions, add them to the context
    if not user_can_subscribe:
        context["user"] = user

    return render(request, get_app_template("newsletters.html"), context)
