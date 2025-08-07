from apps import bouncer_blocklisted
from django.shortcuts import render

from thedaily.utils import unsubscribed_newsletters, get_app_template


def index(request):
    """
    Vista para mostrar y gestionar las newsletters disponibles para suscripción.
    
    Args:
        request: HttpRequest object
        
    Returns:
        HttpResponse: Template renderizado con la lista de newsletters
    """
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
    
    # Ordenar alfabéticamente por el nombre de la newsletter
    try:
        unsubscribed_list = sorted(
            unsubscribed_list, 
            key=lambda x: x.name.lower()
        )
    except (AttributeError, TypeError) as e:
        # Fallback: si hay problemas con el ordenamiento, mantener lista original
        # AttributeError: cuando un objeto no tiene atributo 'name'
        # TypeError: cuando 'name' existe pero no es string (ej: None, 123, etc.)
        pass
    

    context = {
        "unsubscribed_newsletters": unsubscribed_list,
        "show_newsletters_pill": True,
    }

    # Si el usuario no cumple las condiciones, lo añadimos al contexto
    if not user_can_subscribe:
        context["user"] = user

    return render(request, get_app_template("newsletters.html"), context)
