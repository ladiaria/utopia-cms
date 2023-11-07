# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from django.urls import path, re_path
from django.views.generic import TemplateView, RedirectView
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import never_cache
from django.contrib.auth import views as auth_views

from thedaily.views import (
    subscribe,
    referrals,
    google_phone,
    user_profile,
    users_api,
    signup,
    edit_profile,
    update_user_from_crm,
    confirm_email,
    password_change,
    password_reset,
    complete_signup,
    login,
    amp_access_authorization,
    amp_access_pingback,
    session_refresh,
    nlunsubscribe,
    welcome,
    nl_category_subscribe,
    nl_category_unsubscribe,
    communication_subscribe,
    disable_profile_property,
    notification_preview,
    phone_subscription,
    custom_api,
    nl_subscribe,
    nl_auth_subscribe,
    email_check_api,
    most_read_api,
    read_articles_percentage_api,
    last_read_api,
    user_comments_api,
    lista_lectura_leer_despues,
    lista_lectura_favoritos,
    lista_lectura_historial,
    lista_lectura_toggle,
    subscribe_notice_closed,
    nl_track_open_event,
)


# Used to override some views
views_custom_module = getattr(settings, 'THEDAILY_VIEWS_CUSTOM_MODULE', None)
if views_custom_module:
    signup = __import__(views_custom_module, fromlist=['signup']).signup
    google_phone = __import__(views_custom_module, fromlist=['google_phone']).google_phone
    confirm_email = __import__(views_custom_module, fromlist=['confirm_email']).confirm_email
    edit_profile = __import__(views_custom_module, fromlist=['edit_profile']).edit_profile
    complete_signup = __import__(views_custom_module, fromlist=['complete_signup']).complete_signup
    password_reset = __import__(views_custom_module, fromlist=['password_reset']).password_reset
    phone_subscription = __import__(views_custom_module, fromlist=['phone_subscription']).phone_subscription
    amp_access_authorization = __import__(
        views_custom_module, fromlist=['amp_access_authorization']
    ).amp_access_authorization

# Used to override some urls
urls_custom_module = getattr(settings, 'THEDAILY_URLS_CUSTOM_MODULE', None)
if urls_custom_module:
    custom_patterns = __import__(urls_custom_module, fromlist=['urlpatterns']).urlpatterns
else:
    custom_patterns = [
        path('planes/', RedirectView.as_view(url='/usuarios/suscribite/DDIGM/'), name="subscribe_landing")
    ]

urlpatterns = [
    path('', RedirectView.as_view(url='perfil/editar/')),
    path('comentarios/', never_cache(TemplateView.as_view(template_name='thedaily/templates/comments.html'))),
] + custom_patterns + [
    re_path(r'^suscribite/(?P<planslug>\w+)/$', subscribe, name="subscribe"),
    re_path(r'^suscribite/(?P<planslug>\w+)/(?P<category_slug>\w+)/$', subscribe, name="subscribe"),
    path('api/', users_api),
    path('api/custom/', custom_api),
    path('api/email_check/', email_check_api),
    path('api/most_read/', most_read_api),
    path('api/read_articles_percentage/', read_articles_percentage_api),
    path('api/last_read/', last_read_api),
    path('api/comments/', user_comments_api),
    path('fromcrm', update_user_from_crm),
    path('subscribe-notice-closed', subscribe_notice_closed, name='subscribe-notice-closed'),
    # Profile
    path('perfil/editar/', edit_profile, name="edit-profile"),
    re_path(
        r'^perfil/disable/(?P<property_id>[\w_]+)/(?P<hashed_id>\w+)/$',
        disable_profile_property,
        name="disable-profile-property",
    ),
    path('perfil/<int:user_id>/', user_profile, name="user-profile"),

    path('registrate/', signup, name="account-signup"),
    path('registrate/google/', google_phone, name="account-google"),
    path('salir/', auth_views.LogoutView.as_view(next_page='/usuarios/sesion-cerrada/'), name="account-logout"),
    path('sesion-cerrada/', never_cache(TemplateView.as_view(template_name='registration/logged_out.html'))),
    path(
        'salir-invalid/',
        auth_views.LogoutView.as_view(next_page='/usuarios/sesion-finalizada/'),
        name="account-invalid",
    ),
    path('sesion-finalizada/', never_cache(TemplateView.as_view(template_name='registration/session_invalid.html'))),
    path('bienvenida/', welcome, {'signup': True}, name="account-welcome"),
    path('bienvenido/', welcome, {'subscribed': True}, name="account-welcome-s"),

    path('cambiar-password/', password_change, name="account-password_change"),
    path(
        'cambiar-password/hecho/',
        never_cache(TemplateView.as_view(template_name='thedaily/templates/password_change_done.html')),
        name="account-password_change-done",
    ),
    re_path(
        r'^cambiar-password/(?P<user_id>\d{1,})-(?P<hash>.*)/$', password_reset, name='account-password_change-hash'
    ),
    re_path(r'^completar-registro/(?P<user_id>\d{1,})-(?P<hash>.*)/$', complete_signup, name="account-signup-hash"),
    path('entrar/', login, name="account-login"),
    path(
        'error/login/',
        never_cache(TemplateView.as_view(template_name='thedaily/templates/login_error.html')),
        name="login-error",
    ),
    path(
        'error/toomuch/',
        never_cache(TemplateView.as_view(template_name='thedaily/templates/toomuch.html')),
        name="account-error-toomuch",
    ),
    path('restablecer/', password_reset, name="account-password_reset"),
    path(
        'restablecer/correo-enviado/',
        never_cache(TemplateView.as_view(template_name='thedaily/templates/password_reset_mail_sent.html')),
        name="account-password_reset-mail_sent",
    ),
    path('confirm_email/', confirm_email, name='account-confirm_email'),
    path('session_refresh/', session_refresh, name='session-refresh'),

    # TODO: enter "bienvenido/" directly should not be allowed
    path(
        'bienvenido/tel/',
        never_cache(TemplateView.as_view(template_name='thedaily/templates/phone_subscription_thankyou.html')),
        name="telsubscribe_success",
    ),

    # TODO: "referidos" template should be de-customized
    re_path(r'^referidos/(?P<hashed_id>\w+)/$', referrals, name="referrals"),

    re_path(r'^nlunsubscribe/(?P<publication_slug>\w+)/(?P<hashed_id>\w+)/$', nlunsubscribe, name="nlunsubscribe"),
    path('nlsubscribe/', nl_subscribe, name="nl-subscribe"),  # can be useful if a "next" session variable was set
    re_path(r'^nlsubscribe/(?P<nltype>[pc])\.(?P<nlslug>\w+)/$', nl_auth_subscribe, name="nl-auth-subscribe"),
    re_path(r'^nlsubscribe/c/(?P<slug>\w+)/$', nl_category_subscribe, name="nl-category-subscribe"),
    re_path(r'^nlsubscribe/c/(?P<slug>\w+)/(?P<hashed_id>\w+)/$', nl_category_subscribe, name="nl-category-subscribe"),
    re_path(r'^nlsubscribe/(?P<publication_slug>\w+)/(?P<hashed_id>\w+)/$', nl_subscribe, name="nl-subscribe"),
    re_path(
        r'^nlunsubscribe/c/(?P<category_slug>\w+)/(?P<hashed_id>\w+)/$',
        nl_category_unsubscribe,
        name="nl-category-unsubscribe",
    ),
    re_path(
        r'^nl_track/(?P<s8r_or_registered>[sr])_(?P<hashed_id>\w+)_(?P<nl_campaign>\w+)_(?P<nl_date>\d{8}).gif$',
        nl_track_open_event,
        name="nl-track-open-event",
    ),
    re_path(r'^communication-subscribe/(?P<com_type>\w+)/$', communication_subscribe, name="communication-subscribe"),

    path('amp-access/authorization', amp_access_authorization, name="amp-access-authorization"),
    path('amp-access/pingback', amp_access_pingback, name="amp-access-pingback"),

    path('suscribite-por-telefono/', phone_subscription, name="phone-subscription"),

    re_path(r'^notification_preview/(?P<template>[\w]+)/$', notification_preview, name="notification_preview"),
    re_path(
        r'^notification_preview/(?P<template>[\w]+)/days/$',
        notification_preview,
        {'days': True},
        name="notification_preview",
    ),
    path('lista-lectura-leer-despues/', lista_lectura_leer_despues, name="lista-lectura-leer-despues"),
    path('lista-lectura-favoritos/', lista_lectura_favoritos, name="lista-lectura-favoritos"),
    path('lista-lectura-historial/', lista_lectura_historial, name="lista-lectura-historial"),
    re_path(
        r'^lista-lectura-toggle/(?P<event>add|remove|favToggle)/(?P<article_id>\d+)/$',
        lista_lectura_toggle,
        name="lista-lectura-toggle",
    ),
]
