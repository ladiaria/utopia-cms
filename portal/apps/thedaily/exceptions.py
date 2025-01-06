
from builtins import str

from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _


CONTACT_ACTION = _("contactate")  # TODO: test this translation is working
MSG_ERR_UPDATE = f"No fue posible actualizar %s, {CONTACT_ACTION} con nosotros"


class UpdateCrmEx(ValueError):
    def __init__(self, displaymessage=None):
        self.displaymessage = displaymessage

    def __str__(self):
        return "Unable to comunicate with CRM (%s)" % str(self.displaymessage)


class EmailValidationError(ValidationError):
    INVALID = "invalid"
