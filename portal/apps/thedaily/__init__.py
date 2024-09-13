from pycountry import countries

from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def conf_check(app_configs, **kwargs):
    errors, api_uri_varname, api_key_varname = [], "CRM_API_UPDATE_USER_URI", "CRM_UPDATE_USER_API_KEY"

    try:
        countries.get(alpha_2=settings.LOCAL_COUNTRY)
    except LookupError:
        errors.append(
            Error(
                f"Invalid value '{settings.LOCAL_COUNTRY}' for LOCAL_COUNTRY",
                hint="Check your local_settings.py file and assign a valid alpha_2 country code to LOCAL_COUNTRY",
                obj=settings,
            )
        )

    api_uri, api_key = getattr(settings, api_uri_varname), getattr(settings, api_key_varname, None)
    if settings.CRM_UPDATE_USER_ENABLED and not (api_uri and api_key):
        s_missing, hint_val = (api_uri_varname, '(ex.: "utopia-crm.local/api/updateuserweb/")') if not api_uri else (
            api_key_varname, "with an api key generated in CRM"
        )
        errors.append(
            Warning(
                'CRM_UPDATE_USER_ENABLED is True but no %s was set.' % s_missing,
                hint='Set %s in local_settings.py %s' % (s_missing, hint_val),
                obj=settings,
                id='thedaily.W001',
            )
        )
    return errors
