from django.conf import settings
from django.core.checks import Warning, register


@register()
def conf_check(app_configs, **kwargs):
    errors = []
    if settings.CRM_UPDATE_USER_ENABLED and not settings.CRM_API_UPDATE_USER_URI:
        errors.append(
            Warning(
                'CRM_UPDATE_USER_ENABLED is True but no CRM_API_UPDATE_USER_URI was set.',
                hint='Set CRM_API_UPDATE_USER_URI in local_settings.py (ex.: "utopia-crm.local/api/updateuserweb/")',
                obj=settings,
                id='thedaily.W001',
            )
        )
    return errors
