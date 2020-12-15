
from django.contrib.admin import ModelAdmin, site

from models import Serie, Suscripcion, Attribution


class SerieAdmin(ModelAdmin):
    list_display = ('serie', 'min_new_voter')
    search_fields = ('serie', )


class SuscripcionAdmin(ModelAdmin):
    list_display = (
        'subscriber', 'email', 'user_status', 'is_subscriber', 'customer_id',
        'credencial_serie', 'credencial_numero')
    raw_id_fields = ('subscriber', )
    search_fields = (
        'subscriber__name', 'subscriber__user__email',
        'subscriber__user__first_name', 'subscriber__user__last_name',
        'credencial_serie__serie', 'credencial_numero')


class AttributionAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'email', 'amount')
    search_fields = ('name', 'phone', 'email')


site.register(Serie, SerieAdmin)
site.register(Suscripcion, SuscripcionAdmin)
site.register(Attribution, AttributionAdmin)
