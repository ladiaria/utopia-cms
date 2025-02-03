from os.path import join
import locale
from pycountry import countries

from django.conf import settings
from django.core.checks import Error, Warning, register
from django.template import Engine
from django.template.exceptions import TemplateDoesNotExist


def get_talk_url():
    return getattr(settings, 'TALK_URL', None)


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
    else:
        try:
            locale.setlocale(locale.LC_ALL, settings.LOCALE_NAME)
        except locale.Error as lerr:
            errors.append(
                Error(
                    f"{lerr}: {settings.LOCALE_NAME}",
                    hint="Check your local_settings.py file, the LOCALE_NAME locale must be available in your system",
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


def get_app_template(relative_path):
    """
    This simplifies the use of one custom setting per file, but cannot map a known template to any file, if one day
    this became a requirement, we can add a map setting to map the relative_path received here to whatever the custom
    map says; for ex: relative_path = getattr(settings, "NEW_CUSTOM_SETTING", {}).get(relative_path, relative_path)
    where NEW_CUSTOM_SETTING can be for ex: {"welcome.html": "goodbye.html"}
    """
    default_dir, custom_dir = "thedaily/templates", getattr(settings, "THEDAILY_ROOT_TEMPLATE_DIR", None)
    template = join(default_dir, relative_path)  # fallback to the default
    if custom_dir:
        engine = Engine.get_default()
        # search under custom and take it if found
        template_try = join(custom_dir, relative_path)
        try:
            engine.get_template(template_try)
        except TemplateDoesNotExist:
            pass
        else:
            template = template_try
    # if custom dir is not defined, no search is needed
    return template
