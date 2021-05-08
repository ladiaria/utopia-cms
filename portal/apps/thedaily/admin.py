# -*- coding: utf-8 -*-
from django.contrib.admin import ModelAdmin, site
from django.contrib.admin.sites import AlreadyRegistered

from libs.tokens.email_confirmation import send_validation_email, get_signup_validation_url
from thedaily.models import (
    Subscription, ExteriorSubscription, WebSubscriber, Subscriber, SentMail, SubscriberEditionDownloads,
    EditionDownload, SubscriptionPrices)


class SubscriptionAdmin(ModelAdmin):
    list_display = ('id', 'subscriber', 'first_name', 'telephone', 'email', 'get_subscription_type_prices')
    search_fields = ('first_name', 'email', 'subscriber__email')
    raw_id_fields = ('subscriber', )
    exclude = ('subscription_type', )


class ExteriorSubscriptionAdmin(SubscriptionAdmin):
    list_display = (
        'id', 'subscriber', 'first_name', 'document', 'email', 'telephone', 'country', 'city', 'address',
        'observations')
    exclude = (
        'subscription_type', 'last_name', 'province', 'subscription_plan', 'credit_card', 'friend1_name',
        'friend1_email', 'friend1_telephone', 'friend2_name', 'friend2_email', 'friend2_telephone', 'friend3_name',
        'friend3_email', 'friend3_telephone', 'public_profile', 'subscription_type_prices')


class SubscriberAdmin(ModelAdmin):
    list_display = (
        'id', 'costumer_id', 'user', 'user_is_active', 'user_email', 'name', 'pdf', 'activo', 'get_newsletters'
    )
    search_fields = ('user__username', 'name', 'user__email', 'costumer_id', 'document', 'phone')
    raw_id_fields = ('user', )
    readonly_fields = (
        'pdf',
        'lento_pdf',
        'ruta',
        'plan_id',
        'ruta_lento',
        'ruta_fs',
        'days',
        'get_latest_article_visited',
    )
    list_filter = ['newsletters', 'category_newsletters', 'pdf', 'allow_news', 'allow_promotions', 'allow_polls']
    actions = ['send_account_info']
    fieldsets = (
        (None, {
            'fields': (
                ('costumer_id', 'user', 'name'),
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
                send_validation_email(
                    u'Ingreso al sitio web', s.user, 'notifications/account_info.html', get_signup_validation_url,
                    {'user_email': s.user.email})
                SentMail.objects.create(subscriber=s, subject=u'Account info')
                success_counter += 1
            except Exception:
                errors.append(unicode(s))
        self.message_user(request, "%d emails enviados.%s" % (
            success_counter,
            (" Error al enviar a: %s" % ', '.join(errors)) if errors else ""))

    send_account_info.short_description = u"Enviar información de usuario"


class SubscriptionPricesAdmin(ModelAdmin):
    list_display = (
        'id', 'subscription_type', 'price', 'order', 'auth_group', 'ga_sku', 'ga_name', 'ga_category', 'publication')
    list_editable = ('subscription_type', 'price', 'order', 'auth_group', 'publication')


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
