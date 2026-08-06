from apps import bouncer_blocklisted
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from thedaily.utils import ONBOARDING_ARTICLE_SESSION_KEY, unsubscribed_newsletters, get_app_template


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

    # Check if user just registered (from welcome URL parameter). Being logged in is part of it: these buttons belong
    # to the onboarding of somebody who just created an account, and "Continuar" goes to a page that turns anonymous
    # visitors away, so offering it to one is a dead end. The parameter alone survives a shared or bookmarked url, and
    # a session that ends mid-onboarding leaves the reader on this page with a button that cannot work.
    show_welcome_buttons = request.GET.get('welcome') == '1' and user.is_authenticated

    # When the signup started at the registration wall of an article, that article is what the reader wanted in the
    # first place, so the way out of the onboarding leads back to it instead of to the home page. Read and not
    # consumed: this is a link the reader may never click, the screen that closes the onboarding offers the article
    # again, and popping it here would leave that one with nothing. Empty for every other way in (an account created
    # from the signup page, a reader who came from the home page), and those keep offering the home page.
    onboarding_article_url = request.session.get(ONBOARDING_ARTICLE_SESSION_KEY) if show_welcome_buttons else None

    context = {
        "unsubscribed_newsletters": unsubscribed_list,
        "show_newsletters_pill": True,
        "show_welcome_buttons": show_welcome_buttons,
        "onboarding_article_url": onboarding_article_url,
        "current_unsubscribed_nl": request.GET.get("nl", "")
    }

    # If the user doesn't meet the conditions, add them to the context
    if not user_can_subscribe:
        context["user"] = user
    return render(request, get_app_template("newsletters.html"), context)
