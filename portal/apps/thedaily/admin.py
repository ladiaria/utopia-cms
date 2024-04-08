# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str

from django.conf import settings
from django.http import HttpResponseRedirect
from django.db.models.deletion import Collector
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.admin import ModelAdmin, site
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.messages import constants as messages

from libs.tokens.email_confirmation import send_validation_email, get_signup_validation_url
from .models import (
    Subscription,
    ExteriorSubscription,
    WebSubscriber,
    Subscriber,
    SentMail,
    SubscriberEditionDownloads,
    EditionDownload,
    SubscriptionPrices,
    OAuthState,
    RemainingContent,
    MailtrainList,
)
from .utils import collector_analysis
from .exceptions import UpdateCrmEx


class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "first_name", "last_name", "is_active", "is_staff")

    def change_view(self, request, object_id, form_url='', extra_context=None):
        result = None
        try:
            result = super().change_view(request, object_id, form_url, extra_context)
        except UpdateCrmEx:
            self.message_user(
                request, 'Error de comunicación con el CRM, no se aplicaron los cambios', level=messages.ERROR
            )
            result = HttpResponseRedirect(request.get_full_path())
        return result


class SubscriptionAdmin(ModelAdmin):
    list_display = ('id', 'subscriber', 'first_name', 'telephone', 'email', 'get_subscription_type_prices')
    search_fields = ('first_name', 'email', 'subscriber__email')
    raw_id_fields = ('subscriber', )
    exclude = ('subscription_type', )


class ExteriorSubscriptionAdmin(SubscriptionAdmin):
    list_display = (
        'id',
        'subscriber',
        'first_name',
        'document',
        'email',
        'telephone',
        'country',
        'city',
        'address',
        'observations',
    )
    exclude = (
        'subscription_type',
        'last_name',
        'province',
        'subscription_plan',
        'friend1_name',
        'friend1_email',
        'friend1_telephone',
        'friend2_name',
        'friend2_email',
        'friend2_telephone',
        'friend3_name',
        'friend3_email',
        'friend3_telephone',
        'public_profile',
        'subscription_type_prices',
    )


class SubscriberAdmin(ModelAdmin):
    list_display = (
        'id', 'contact_id', 'user', 'user_is_active', 'user_email', 'name', 'pdf', 'get_newsletters'
    )
    search_fields = ("id", "user__id", 'user__username', 'name', 'user__email', 'contact_id', 'document', 'phone')
    raw_id_fields = ('user', )
    readonly_fields = (
        'pdf',
        'lento_pdf',
        'ruta',
        'plan_id',
        'ruta_lento',
        'ruta_fs',
        'get_latest_article_visited',
    )
    list_filter = ['newsletters', 'category_newsletters', 'pdf', 'allow_news', 'allow_promotions', 'allow_polls']
    actions = ['send_account_info', "delete_user"]
    fieldsets = (
        (None, {
            'fields': (
                ('contact_id', 'user', 'name'),
                ('address', 'country', 'city', 'province'),
                ('document', 'phone'),
                ('newsletters', 'category_newsletters'),
                ('allow_news', 'allow_promotions', 'allow_polls'),
                ('pdf', 'ruta'),
                ('plan_id', ),
                ('get_latest_article_visited', ),
            ),
        }),
    )

    def send_account_info(self, request, queryset):
        success_counter, errors = 0, []
        for s in queryset:
            try:
                was_sent = send_validation_email(
                    'Ingreso al sitio web',
                    s.user,
                    'notifications/account_info.html',
                    get_signup_validation_url,
                    {'user_email': s.user.email},
                )
                if not was_sent:
                    raise Exception("El email de notificación para el usuario: %s no pudo ser enviado." % s.user)
                SentMail.objects.create(subscriber=s, subject='Account info')
                success_counter += 1
            except Exception:
                errors.append(str(s))
        self.message_user(
            request,
            "%d emails enviados.%s" % (
                success_counter, (" Error al enviar a: %s" % ', '.join(errors)) if errors else ""
            ),
        )

    def delete_user(self, request, queryset):
        msg_err, msg_success = None, None
        if queryset.count() > 1:
            msg_err = "La acción no permite seleccionar más de un suscriptor"
        else:
            s = queryset[0]
            u = s.user
            if s.plan_id or u.is_active or u.is_staff or u.is_superuser:
                msg_err = "No se permite eliminar usuarios 'staff' o usuarios activos"
            else:
                collector = Collector(using='default')
                collector.collect([u])
                safe_to_delete, msg_err = collector_analysis(collector.data)
                if safe_to_delete:
                    try:
                        u.delete()
                    except Exception as e:
                        message = e.message  # noqa
                    else:
                        msg_success = "El suscriptor seleccionado y su usuario fueron eliminados correctamente"
                else:
                    msg_err = "El conjunto de datos relacionados al usuario que se pretende eliminar se considera " \
                              "importante o demasiado grande: %s" % msg_err
        if msg_success:
            self.message_user(request, msg_success)
        else:
            self.message_user(request, msg_err, level=messages.ERROR)

    def save_model(self, request, obj, form, change):
        if form.is_valid():
            try:
                super().save_model(request, obj, form, change)
                # delete possible non-finished google signin (now is finished)
                OAuthState.objects.get(user=obj.user).delete()
            except OAuthState.DoesNotExist:
                pass
            except Exception as e:
                if settings.DEBUG:
                    print(e)

    send_account_info.short_description = "Enviar información de usuario"
    delete_user.short_description = "Eliminar suscriptor y usuario asociado"


class SubscriptionPricesAdmin(ModelAdmin):
    list_display = ('id', 'subscription_type', 'price', 'order', 'auth_group', 'publication')
    list_editable = ('subscription_type', 'price', 'order', 'auth_group', 'publication')


class RemainingContentAdmin(ModelAdmin):
    list_display = ("remaining_articles", "template_content")


class MailtrainListAdmin(ModelAdmin):
    list_display = ("newsletter_name", "list_cid", "on_signup", "newsletter_new_pill")
    list_editable = ("on_signup", "newsletter_new_pill")


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

site.register(Subscription, SubscriptionAdmin)
site.register(ExteriorSubscription, ExteriorSubscriptionAdmin)
site.register(WebSubscriber)
try:
    # avoid error if this model was already registered elsewhere
    site.register(Subscriber, SubscriberAdmin)
except AlreadyRegistered:
    pass
site.register(SubscriberEditionDownloads)
site.register(EditionDownload)
site.register(SubscriptionPrices, SubscriptionPricesAdmin)
site.register(RemainingContent, RemainingContentAdmin)
site.register(MailtrainList, MailtrainListAdmin)
