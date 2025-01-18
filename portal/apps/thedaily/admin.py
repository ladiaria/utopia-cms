# -*- coding: utf-8 -*-

from builtins import str

from django.conf import settings
from django.http import HttpResponseRedirect
from django.db import IntegrityError
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
from . import get_app_template


class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "first_name", "last_name", "is_active", "is_staff")

    def change_view(self, request, object_id, form_url='', extra_context=None):
        result = None
        try:
            result = super().change_view(request, object_id, form_url, extra_context)
        except IntegrityError as ie:
            self.message_user(request, str(ie), level=messages.ERROR)
            result = HttpResponseRedirect(request.get_full_path())
        except UpdateCrmEx:
            self.message_user(
                request, 'Error de comunicación con el CRM, no se aplicaron los cambios', level=messages.ERROR
            )
            result = HttpResponseRedirect(request.get_full_path())
        return result


class SubscriptionAdmin(ModelAdmin):
    list_display = (
        'id',
        'subscriber',
        'billing_name',
        'billing_phone',
        'billing_email',
        'get_subscription_type_prices'
    )
    search_fields = ('billing_name', 'billing_email', 'subscriber__email')
    raw_id_fields = ('subscriber',)
    exclude = ('subscription_type',)


class ExteriorSubscriptionAdmin(SubscriptionAdmin):
    list_display = (
        'id',
        'subscriber',
        'billing_name',
        'billing_id_doc',
        'billing_email',
        'billing_phone',
        'country',
        'city',
        'address',
    )
    exclude = (
        'subscription_type',
        'province',
        'subscription_type_prices',
    )


class SubscriberAdmin(ModelAdmin):
    list_display = (
        'id', 'contact_id', "repr", 'user_id', 'user_is_active', 'user_email', 'get_newsletters'
    )
    search_fields = (
        "id",
        "user__id",
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'contact_id',
        'document',
        'phone'
    )
    raw_id_fields = ('user',)
    readonly_fields = ("extra_info", 'plan_id', 'get_latest_article_visited')
    list_filter = ['newsletters', 'category_newsletters', 'allow_news', 'allow_promotions', 'allow_polls']
    actions = ['send_account_info', "delete_user"]  # TODO: new action: sync_plan_id_from_activos_csv
    fieldsets = (
        (None, {
            'fields': (
                ('contact_id', 'user'),
                ('address', 'country'),
                ('city', 'province'),
                ('document', 'phone'),
                ('newsletters', 'category_newsletters'),
                ('allow_news', 'allow_promotions', 'allow_polls'),
                ('extra_info',),
                ('plan_id',),
                ('get_latest_article_visited',),
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
                    get_app_template('notifications/account_info.html'),
                    get_signup_validation_url,
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
    list_display = (
        '__str__', "subscription_type", 'order', 'months', 'price', 'price_total', "discount", 'publication'
    )
    list_editable = list_display[1:]

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name in ('price', 'price_total'):
            field.widget.attrs['style'] = 'width:8em;'
        elif db_field.name == 'discount':
            field.widget.attrs['style'] = 'width:5em;'
        elif db_field.name in ('order', 'months'):
            field.widget.attrs['style'] = 'width:3em;'
        elif db_field.name == 'extra_info':
            field.required = False
            field.widget.attrs = {'style': 'width:80%;font-family:monospace', 'spellcheck': "false", 'rows': 10}
        return field


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
