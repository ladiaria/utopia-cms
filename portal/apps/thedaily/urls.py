# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import url
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
    edit_subscription,
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
    disable_profile_property,
    notification_preview,
    phone_subscription,
    custom_api,
    nl_subscribe,
    email_check_api,
    user_comments_api,
    lista_lectura_leer_despues,
    lista_lectura_favoritos,
    lista_lectura_historial,
    lista_lectura_toggle,
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
    custom_patterns = [url(
        r'^planes/$', RedirectView.as_view(url='/usuarios/suscribite/DDIGM/'), name="subscribe_landing")]

urlpatterns = [
    url(r'^$', RedirectView.as_view(url='perfil/editar/')),
    url(r'^comentarios/$', never_cache(TemplateView.as_view(template_name='thedaily/templates/comments.html')))
] + custom_patterns + [
    url(r'^suscribite/(?P<planslug>\w+)/$', subscribe, name="subscribe"),
    url(r'^suscribite/(?P<planslug>\w+)/(?P<category_slug>\w+)/$', subscribe, name="subscribe"),
    url(r'^api/$', users_api),
    url(r'^api/custom/$', custom_api),
    url(r'^api/email_check/$', email_check_api),
    url(r'^api/comments/$', user_comments_api),
    url(r'^fromcrm$', update_user_from_crm),
    url(r'^suscripcion/editar$', edit_subscription, name="edit-subscription"),
    # Profile
    url(r'^perfil/editar/$', edit_profile, name="edit-profile"),
    url(
        r'^perfil/disable/(?P<property_id>[\w_]+)/(?P<hashed_id>\w+)/$',
        disable_profile_property,
        name="disable-profile-property",
    ),
    url(r'^perfil/(?P<user_id>\d+)/$', user_profile, name="user-profile"),

    url(r'^registrate/$', signup, name="account-signup"),
    url(
        r'^cambiar-password/hecho/$',
        vary_on_cookie(TemplateView.as_view(template_name='thedaily/templates/password_change_done.html')),
        name="account-password_change-done"
    ),
    url(r'^registrate/google/$', google_phone, name="account-google"),
    url(r'^salir/$', auth_views.LogoutView.as_view(next_page='/usuarios/sesion-cerrada/'), name="account-logout"),
    url(r'^sesion-cerrada/$', never_cache(TemplateView.as_view(template_name='registration/logged_out.html'))),
    url(
        r'^salir-invalid/$',
        auth_views.LogoutView.as_view(next_page='/usuarios/sesion-finalizada/'),
        name="account-invalid",
    ),
    url(r'^sesion-finalizada/$', never_cache(TemplateView.as_view(template_name='registration/session_invalid.html'))),
    url(r'^bienvenida/$', welcome, {'signup': True}, name="account-welcome"),
    url(r'^bienvenido/$', welcome, {'subscribed': True}, name="account-welcome-s"),

    url(r'^cambiar-password/$', password_change, name="account-password_change"),
    url(r'^cambiar-password/hecho/$', never_cache(TemplateView.as_view(
        template_name='thedaily/templates/password_change_done.html')),
        name="account-password_change-done"),
    url(r'^cambiar-password/(?P<user_id>\d{1,})-(?P<hash>.*)/$', password_reset, name='account-password_change-hash'),
    url(r'^completar-registro/(?P<user_id>\d{1,})-(?P<hash>.*)/$', complete_signup, name="account-signup-hash"),
    url(r'^entrar/$', login, name="account-login"),
    url(r'^error/login/$', never_cache(TemplateView.as_view(
        template_name='thedaily/templates/login_error.html')),
        name="login-error"),
    url(r'^error/toomuch/$', never_cache(TemplateView.as_view(
        template_name='thedaily/templates/toomuch.html')),
        name="account-error-toomuch"),
    url(r'^restablecer/$', password_reset, name="account-password_reset"),
    url(r'^restablecer/correo-enviado/$', never_cache(TemplateView.as_view(
        template_name='thedaily/templates/password_reset_mail_sent.html')),
        name="account-password_reset-mail_sent"),
    url(r'^confirm_email/$', confirm_email, name='account-confirm_email'),
    url(r'^session_refresh/$', session_refresh, name='session-refresh'),

    # TODO: enter "bienvenido/" directly should not be allowed
    # TODO: first 2 urls are custom and should be removed
    url(r'^ldfs/bienvenido/$', never_cache(TemplateView.as_view(
        template_name='thedaily/templates/ldfs_thankyou.html')), name="ldfssubscribe_success"),
    url(r'^educacion/bienvenido/$', never_cache(TemplateView.as_view(
        template_name='thedaily/templates/edu_thankyou.html')),
        name="edusubscribe_success"),
    url(r'^bienvenido/tel/$', never_cache(TemplateView.as_view(
        template_name='thedaily/templates/phone_subscription_thankyou.html')),
        name="telsubscribe_success"),

    url(r'^referidos/(?P<hashed_id>\w+)/$', referrals, name="referrals"),
    url(r'^nlunsubscribe/(?P<publication_slug>\w+)/(?P<hashed_id>\w+)/$', nlunsubscribe, name="nlunsubscribe"),
    url(r'^nlsubscribe/$', nl_subscribe, name="nl-subscribe"),
    url(r'^nlsubscribe/c/(?P<slug>\w+)/$', nl_category_subscribe, name="nl-category-subscribe"),
    url(r'^nlsubscribe/c/(?P<slug>\w+)/(?P<hashed_id>\w+)/$', nl_category_subscribe, name="nl-category-subscribe"),
    url(r'^nlsubscribe/(?P<publication_slug>\w+)/(?P<hashed_id>\w+)/$', nl_subscribe, name="nl-subscribe"),
    url(
        r'^nlunsubscribe/c/(?P<category_slug>\w+)/(?P<hashed_id>\w+)/$',
        nl_category_unsubscribe,
        name="nl-category-unsubscribe",
    ),

    url(r'^amp-access/authorization$', amp_access_authorization),
    url(r'^amp-access/pingback$', amp_access_pingback),

    url(r'^suscribite-por-telefono/$', phone_subscription, name="phone-subscription"),

    url(r'^notification_preview/(?P<template>[\w]+)/$', notification_preview, name="notification_preview"),
    url(
        r'^notification_preview/(?P<template>[\w]+)/days/$',
        notification_preview,
        {'days': True},
        name="notification_preview",
    ),
    url(r'^lista-lectura-leer-despues/$', lista_lectura_leer_despues, name="lista-lectura-leer-despues"),
    url(r'^lista-lectura-favoritos/$', lista_lectura_favoritos, name="lista-lectura-favoritos"),
    url(r'^lista-lectura-historial/$', lista_lectura_historial, name="lista-lectura-historial"),
    url(
        r'^lista-lectura-toggle/(?P<event>add|remove|favToggle)/(?P<article_id>\d+)/$',
        lista_lectura_toggle,
        name="lista-lectura-toggle"),
]
