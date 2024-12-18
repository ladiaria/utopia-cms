from apps import bouncer_blocklisted
from django.shortcuts import render

from thedaily.utils import unsubscribed_newsletters, get_app_template


def index(request):
    user = request.user
    subscriber = getattr(user, 'subscriber', None)

    # Verificar si el usuario puede tener newsletters no suscritas basadas en las condiciones
    user_can_subscribe = (
        user.is_authenticated
        and subscriber is not None
        and user.email
        and user.email not in bouncer_blocklisted
    )

    # Si el usuario puede suscribirse, se le pasan sus datos; en caso contrario se pasa False.
    unsubscribed_list = unsubscribed_newsletters(subscriber if user_can_subscribe else False, False)

    context = {
        "unsubscribed_newsletters": unsubscribed_list
    }

    # Si el usuario no cumple las condiciones, lo añadimos al contexto
    if not user_can_subscribe:
        context["user"] = user

    return render(request, get_app_template("newsletters.html"), context)

