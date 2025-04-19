from content_settings.types.basic import SimpleString

from django.forms import SlugField


THEDAILY_SUBSCRIPTION_TYPE_DEFAULT = SimpleString(
    help="Slug del plan de suscripción predeterminado.", cls_field=SlugField
)
